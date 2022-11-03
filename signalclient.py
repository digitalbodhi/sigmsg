import logging
from asyncio import Event as a_Event
from json.decoder import JSONDecodeError
from aiohttp import web
from YamJam import yamjam

from asyncloop import AsyncLoop
from signalevent import SignalEvent
from signalreceivehandler import SignalReceiveHandler
from signalsendhandler import SignalSendHandler

class SignalClient(AsyncLoop):
    def __init__(self, host, signal_port, rest_port,
                 phone, user, first='', last=''):
        super().__init__('signalclient', log_levels=[logging.NOTSET,
                                                     logging.DEBUG,
                                                     logging.INFO])
        self.debug = False
        self.host = host
        self.signal_port = signal_port
        self.rest_port = rest_port
        self.tasks = [self.connect_and_receive_loop,
                      self.request_handler_loop]
        self.close_signal = self.loop.create_future()
        self.transport_event = a_Event()
        # transport will be set once the transport_event occurs
        self.transport = None
        self.input = SignalReceiveHandler(self)
        self.output = SignalSendHandler(self)
        self.account = phone
        self.name_user = user
        self.name_first = first
        self.name_last = last
        # if this were multithreaded, this would need to be made thread safe
        # but we should be good as a single threaded asyncio app
        self.sent_id = 1

    async def connect_and_receive_loop(self):
        self.transport, protocol = await(self.loop.create_connection(
            lambda: self.input, self.host, self.signal_port))
        # Wait until the protocol signals that the connection
        # is lost and close the transport.
        try:
            await self.close_signal
        finally:
            self.transport.close()

    async def request_handler_loop(self):
        await self.set_account()
        server = web.Server(self.rest_handler)
        runner = web.ServerRunner(server)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.rest_port)
        await site.start()
        self.lgr.debug('request handler started')
        await self.close_signal

    async def rest_handler(self, request):
        try:
            json = await request.json()

            if('recipients' in json and
               hasattr(json['recipients'], '__len__') and
               len(json['recipients']) > 0 and
               'message' in json and
               len(json['message']) > 0):

                # send the message in chunks
                await self.send(
                    json['recipients'],
                    json['message'],
                )
                data = {'success': 'success'}
                return web.json_response(data, status=200)
            else:
                data = {'error': 'must have recipients and message fields'}
                return web.json_response(data, status=200)
        except JSONDecodeError as err:
            data = {'error': 'invalid json format: '+str(err)}
            self.lgr.warning('invalid json')
            return web.json_response(data, status=200)

    def get_next_sent_id(self):
        self.sent_id += 1
        return self.sent_id

    async def send(self, recipients, message):
        msg = SignalEvent.make_message(self.account,
                                       recipients,
                                       message,
                                       msg_id=self.get_next_sent_id())
        await self.send_raw(msg)

    async def send_raw(self, msg):
        await self.output.transmit_message(msg)

    async def set_account(self):
        msg = SignalEvent.make_updateprofile(self.account,
                                             self.name_user,
                                             self.name_first,
                                             self.name_last,
                                             self.get_next_sent_id())
        await self.send_raw(msg)

    async def receive_handler(self, event):
        # output the event
        if(event.get_type() != SignalEvent.TYPE_RECV):
            if(event.get_type() == SignalEvent.TYPE_RESULT):
                self.lgr.debug('result msg: '+str(event))
            elif(event.get_type() == SignalEvent.TYPE_ERROR):
                self.lgr.error('error msg: '+str(event))
            elif(event.get_type() == SignalEvent.TYPE_UNKNOWN):
                self.lgr.warning('unknown msg: '+str(event))
            elif(event.get_type() == SignalEvent.TYPE_SENT):
                self.lgr.debug(event)
            else:
                self.lgr.error('unexpected msg type: '+str(event))
            return
        else:
            if(event.get_subtype() != SignalEvent.SUBTYPE_MESSAGE):
                if(event.get_subtype() == SignalEvent.SUBTYPE_RECEIPT):
                    self.lgr.debug(f'receipt from {event.sender}, {event.get_receipt_type_str()}')
                else:
                    self.lgr.debug(event)
                return

        # acknowledge the receipt of the message
        await event.ack_receipt()

        msg = event.get_message()

        # do something here
        self.lgr.debug(msg)


def main():
    APP_NAME = 'signalclient'
    if(APP_NAME not in yamjam().keys()):
        raise Exception(
            'Startup failed: "config.yaml" is not properly configured')

    YJ = yamjam()[APP_NAME]

    sc = SignalClient(
        YJ['HOST'],
        YJ['SIGNAL_CLI_PORT'],
        YJ['REST_API_PORT'],
        YJ['SIGNAL_ACCOUNT'],
        YJ['SIGNAL_USER'],
        YJ['SIGNAL_FIRST'],
        YJ['SIGNAL_LAST'],
    )

    sc.run_loop()

if __name__ == '__main__':
    main()
