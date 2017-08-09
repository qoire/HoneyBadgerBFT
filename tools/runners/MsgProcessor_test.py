import unittest
from MsgProcessor import MsgProcessor
import zmq
import json

class TestMsgProcessor(unittest.TestCase):

    def test_connection(self):
        # setup zmq connection
        port = 30302
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        socket.bind("tcp://127.0.0.1:%s" % port)

        proc = MsgProcessor()
        proc.run()

        while True:
            msg = socket.recv()
            if msg != None:
                break

        obj = json.loads(msg)
        print(obj)
        if not 'msg_type' in obj:
            self.fail("msg_type not a key")

        if not 'ip' in obj:
            self.fail("ip not a key")

        if not 'port' in obj:
            self.fail("port not a key")

        proc.stop()

        # shutdown our sockets too
        socket.close()
        context.term()

    def test_message_sending(self):
        port = 30302 # default
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        socket.bind("tcp://127.0.0.1:%s" % port)

        proc = MsgProcessor()
        proc.run()