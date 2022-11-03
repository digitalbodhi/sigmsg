class SignalSendHandler:

    def __init__(self, caller):
        self.caller = caller
        self.first_time = True

    async def transmit_message(self, json):
        # before we can send, we need to make sure the
        #  we are connected to signal-cli
        if(self.first_time):
            await self.caller.transport_event.wait()
            self.first_time = False

        # all messages are delimited by return
        msg = json + "\n"

        self.caller.lgr.debug(f"sent: {json}")

        # send the message
        self.caller.transport.write(msg.encode('utf-8'))

