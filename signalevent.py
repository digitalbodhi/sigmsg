from pprint import pformat as j_pretty
from random import randint
from json import dumps as j_encode

class SignalEvent:
    TYPE_SENT = 1
    TYPE_RECV = 2
    TYPE_RESULT = 3
    TYPE_ERROR = 4
    TYPE_UNKNOWN = 5
    TYPES = {
        TYPE_SENT: 'sent msg',
        TYPE_RECV: 'recv\'d msg',
        TYPE_RESULT: 'result',
        TYPE_ERROR: 'error',
        TYPE_UNKNOWN: 'unknown',
    }
    SUBTYPE_MESSAGE = 1
    SUBTYPE_RECEIPT = 2
    SUBTYPE_TYPING = 3
    SUBTYPE_SYNC = 4
    SUBTYPE_UNKNOWN = 5
    SUBTYPES = {
        SUBTYPE_MESSAGE: 'message',
        SUBTYPE_RECEIPT: 'receipt',
        SUBTYPE_TYPING: 'typing',
        SUBTYPE_SYNC: 'sync',
        SUBTYPE_UNKNOWN: 'unknown',
    }
    RCPTYPE_DELIVERY = 1
    RCPTYPE_READ = 2
    RCPTYPE_VIEWED = 3
    RCPTYPE_UNKNOWN = 4
    RCPTYPES = {
        RCPTYPE_DELIVERY: 'delivery',
        RCPTYPE_READ: 'read',
        RCPTYPE_VIEWED: 'viewed',
        RCPTYPE_UNKNOWN: 'unknown',
    }

    def __init__(self, json_obj, send_cb, sent_id_cb):
        self.json = json_obj
        self.send_cb = send_cb
        self.sent_id_cb = sent_id_cb
        # event is one of these types:
        self.type = SignalEvent.TYPE_UNKNOWN

        # if sent or recv then one of these types:
        self.subtype = SignalEvent.SUBTYPE_UNKNOWN

        # if this is a result
        self.has_results = False
        self.results = []

        # if message, it may have one or more of these attrs
        self.has_message = False
        self.has_reply = False
        self.has_reaction = False
        self.has_attachment = False

        # actual pieces of info
        self.id = 0
        self.sender = ''
        self.sender_name = ''
        self.sender_uuid = ''

        self.recipient = ''
        self.timestamp = 0
        self.message = ''
        self.re_timestamp = 0

        if('result' in json_obj):
            self.type = SignalEvent.TYPE_RESULT
            self.id = json_obj['id']
            if('results' in json_obj['result']):
                self.results = json_obj['result']['results']
        elif('error' in json_obj):
            self.type = SignalEvent.TYPE_ERROR
            self.id = json_obj['id']
            self.has_message = True
            self.message = json_obj['error']['message']
            if('data' in json_obj['error'] and
               json_obj['error']['data'] and
               'response' in json_obj['error']['data'] and
               json_obj['error']['data']['response'] and
               'results' in json_obj['error']['data']['response']):
                self.results = json_obj['error']['data']['response']['results']
        else:
            if('method' in json_obj):
                if(json_obj['method'] == 'send'):
                    self.type = SignalEvent.TYPE_SENT
                elif(json_obj['method'] == 'receive'):
                    self.type = SignalEvent.TYPE_RECV

        if(self.type == SignalEvent.TYPE_SENT or
           self.type == SignalEvent.TYPE_RECV):
            if('params' in json_obj and
               'account' in json_obj['params'] and
               'envelope' in json_obj['params'] and
               'source' in  json_obj['params']['envelope']):
                self.recipient = json_obj['params']['account']
                envelope = json_obj['params']['envelope']
                self.sender = envelope['source']
                self.sender_name = envelope['sourceName']
                self.sender_uuid = envelope['sourceUuid']

                if('typingMessage' in envelope):
                    self.subtype = SignalEvent.SUBTYPE_TYPING
                elif('receiptMessage' in envelope):
                    self.subtype = SignalEvent.SUBTYPE_RECEIPT
                elif('syncMessage' in envelope):
                    self.subtype = SignalEvent.SUBTYPE_SYNC
                elif('dataMessage' in envelope):
                    self.subtype = SignalEvent.SUBTYPE_MESSAGE
                    dm = envelope['dataMessage']
                    if('message' in dm and dm['message'] != None):
                        self.has_message = True
                        self.message = dm['message']
                    if('quote' in dm):
                        self.has_reply = True
                        self.re_timestamp = dm['quote']['id']
                    if('reaction' in dm):
                        self.has_reaction = True
                        self.message = dm['reaction']['emoji']
                        self.re_timestamp = dm['reaction']['targetSentTimestamp']
                    ##TODO attachment

                self.timestamp = envelope['timestamp']

    async def reply(self, msg_text):
        msg = SignalEvent.make_typing(self.recipient, self.sender, msg_id=self.sent_id_cb())
        await self.send_cb(msg)
        #TODO maybe need to change recipient in groups
        msg = SignalEvent.make_message(self.recipient, self.sender, msg_text, msg_id=self.sent_id_cb())
        await self.send_cb(msg)

    async def ack_receipt(self):
        msg = SignalEvent.make_receipt(self.recipient, self.sender, self.timestamp, msg_id=self.sent_id_cb())
        await self.send_cb(msg)

    def get_type(self):
        return self.type

    def get_subtype(self):
        return self.subtype

    def get_message(self):
        return self.message

    def get_receipt_type(self):
        if(self.subtype == SignalEvent.SUBTYPE_RECEIPT):
            msg = self.json['params']['envelope']['receiptMessage']
            if(msg['isDelivery'] == True):
                ret = SignalEvent.RCPTYPE_DELIVERY
            elif(msg['isRead'] == True):
                ret = SignalEvent.RCPTYPE_READ
            elif(msg['isViewed'] == True):
                ret = SignalEvent.RCPTYPE_VIEWED
            else:
                ret = SignalEvent.RCPTYPE_UNKNOWN
        else:
            ret = SignalEvent.RCPTYPE_UNKNOWN
        return ret

    def get_receipt_type_str(self):
        return SignalEvent.RCPTYPES[self.get_receipt_type()]

    def __str__(self):
        ret = '['+SignalEvent.TYPES[self.type]+']'
        if(self.type == SignalEvent.TYPE_RESULT):
            ret += ' id="'+str(self.id)+'"'
            ret += '\n'+j_pretty(self.json)
        elif(self.type == SignalEvent.TYPE_ERROR):
            ret += ' id="'+str(self.id)+'"'
            ret += ' msg="'+self.message+'"'
            ret += '\n'+j_pretty(self.json)
        elif(self.type == SignalEvent.TYPE_UNKNOWN):
            ret += '\n'+j_pretty(self.json)
        elif(self.subtype == SignalEvent.SUBTYPE_UNKNOWN):
            ret += '\n'+j_pretty(self.json)
        else:
            ret += ' ['+SignalEvent.SUBTYPES[self.subtype]+']'
            ret += ' id="'+str(self.id)+'"'
            ret += ' sender="'+self.sender+'"'
            ret += ' recipient="'+self.recipient+'"'
            ret += ' timestamp="'+str(self.timestamp)+'"'
            if(self.has_message):
               ret += ' msg="'+self.message+'"'
            if(self.has_reply or self.has_reaction):
               ret += ' reply_ts="'+str(self.re_timestamp)+'"'
            if(self.subtype == SignalEvent.SUBTYPE_RECEIPT):
               ret += ' type="'+self.get_receipt_type_str()+'"'
            ##TODO attachment
            # ret += '\n'+j_pretty(self.json)
        return ret

    @staticmethod
    def make_message(sender, recipients, message, attachments=[], msg_id=randint(1, 5000), group=False):
        # sometimes ppl are lazy and forget the array wrapper on recipients
        if(type(recipients) is str):
            recipients = [recipients]

        ret = {
                "jsonrpc": "2.0",
                "method": "send",
                "params":
                    {
                        "account": sender,
                        "message": message
                    },
                "id": msg_id
            }
        if(len(attachments) > 0):
            ret['params']['attachments'] = attachments

        if(group):
            ret['params']['groupId'] = recipients
        else:
            ret['params']['recipients'] = recipients

        return j_encode(ret)

    @staticmethod
    def make_updateprofile(sender, user_n, given_n='', family_n='', msg_id=randint(1, 5000)):
        ret = {
                "jsonrpc": "2.0",
                "method": "updateProfile",
                "params": {
                    "account": sender,
                    "name": user_n,
                    "givenName": given_n,
                    "familyName": family_n,
                    # "about": "",
                    # "aboutEmoji": "",
                    # "avatar": "",
                },
                "id": msg_id
            }
        return j_encode(ret)

    @staticmethod
    def make_typing(sender, recipient, msg_id=randint(1, 5000)):
        ret = {
                "jsonrpc": "2.0",
                "method": "sendTyping",
                "params": {
                    "account": sender,
                    "recipient": recipient,
                },
                "id": msg_id
            }
        return j_encode(ret)

    @staticmethod
    def make_receipt(sender, recipient, timestamp, msg_id=randint(1, 5000)):
        ret = {
                "jsonrpc": "2.0",
                "method": "sendReceipt",
                "params": {
                    "account": sender,
                    "recipient": recipient,
                    "targetTimestamp": timestamp,
                },
                "id": msg_id
            }
        return j_encode(ret)
