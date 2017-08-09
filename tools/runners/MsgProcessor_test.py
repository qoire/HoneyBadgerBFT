import unittest
from MsgProcessor import MsgProcessor
import zmq

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
            print(msg)
