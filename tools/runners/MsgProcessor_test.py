import unittest
from MsgProcessor import MsgProcessor
import zmq
import json
import random

class TestMsgProcessor(unittest.TestCase):

    def test_connection(self):
        port = 30302
        context = zmq.Context()
        socket = context.socket(zmq.PAIR)
        socket.connect("tcp://127.0.0.1:%s" % port)
        socket.send_string("hello")

