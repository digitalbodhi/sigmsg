from asyncio import Protocol as a_Protocol, create_task as a_create_task
from json import loads as j_decode
from pprint import pformat as j_pretty
from json.decoder import JSONDecodeError
from signalevent import SignalEvent

class SignalReceiveHandler(a_Protocol):
    def __init__(self, caller):
        self.caller = caller
        self.json_buffer = ''

    def connection_made(self, transport):
        self.caller.transport = transport
        self.caller.transport_event.set()
        self.caller.lgr.debug('transport connected');

    # sample response to receive
    # {
    #     "jsonrpc": "2.0",
    #     "method": "receive",
    #     "params": {
    #       "envelope": {
    #         "source": "+1XXXXXXXXXX",
    #         "sourceNumber": "+1XXXXXXXXXX",
    #         "sourceUuid": "12345e67-123c-4a56-789e-2345a2e3f4bd",
    #         "sourceName": "D",
    #         "sourceDevice": 1,
    #         "timestamp": 1664746936057,
    #         "dataMessage": {
    #           "timestamp": 1664746936057,
    #           "message": "Ok",
    #           "expiresInSeconds": 0,
    #           "viewOnce": false
    #         }
    #       },
    #       "account": "+1XXXXXXXXXX",
    #       "subscription": 33
    #     }
    #  }
    def data_received(self, data):
        raw = data.decode()

        # check to make sure we are at the end of
        # json transmission, if we aren't, buffer
        if(raw[len(raw) - 1] != '\n'):
            # we need to save this
            # self.caller.lgr.info('buffering json:\n\t'+self.json_buffer+'\n\twith:\n\t'+raw)
            self.json_buffer += raw;
            return
        else:
            # otherwise, let more forward and clear the buffer
            if(self.json_buffer != ''):
                raw = self.json_buffer + raw
                self.json_buffer = ''

        if(len(raw) <= 1):
            # sometimes we just get return characters
            # so when we do, ignore it
            return

        try:
            #sometimes we get multiple messages
            raws = raw.split('\n')
            for cmd in raws:
                # the 2nd val in cmd can be an empty value if it was a normal
                # message with just a json and a return vs json, return, json
                if(cmd):
                    ret = j_decode(cmd);
                    if(self.caller.debug):
                       self.caller.lgr.debug("\n"+j_pretty(ret))

                    self.caller.loop.create_task(self.caller.receive_handler(SignalEvent(ret, self.caller.send_raw, self.caller.get_next_sent_id)))
        except JSONDecodeError as e:
            self.caller.lgr.error('json err: '+str(e)+", raw:\n"+ j_pretty(raw))

    def eof_received(self):
        self.caller.lgr.warning('signal-cli daemon signaled no more data')
        if(self.caller.close_signal and not (self.caller.close_signal.done() or self.caller.close_signal.cancelled())):
                self.caller.close_signal.set_result(True)

    def connection_lost(self, exc):
        self.caller.lgr.error('signal-cli daemon connection was closed')
        if(self.caller.close_signal and not (self.caller.close_signal.done() or self.caller.close_signal.cancelled())):
            self.caller.close_signal.set_result(True)
        a_create_task(self.caller.shutdown())
