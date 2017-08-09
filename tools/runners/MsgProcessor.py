import socket
import gevent
import json
import base64
import Queue
from gevent import Greenlet

'''
MsgProcessor class, processes messages between the other components of the kernel
and the consensus algorithms (this), defines a few message types for passing
messages between the two parts of the system, this subroutine should be booted-up
alongside the kernel, and assigned a specific socket port

Composites two greenlets that does most of the heavy lifting. Establishes a two
way connection.

Connection phase happens as such:
1) The other party sets up server first, then calls us (launches)
2) We set up our server, then connect to their server, and send the message:
    {
        msg_type: CONNECT
        host: 127.0.0.1
        port: 30303 (or something like that)
    }

SERVER_SIDE:
Messages should be in the following format:
    {
        msg_type: TX (so far only transaction messages supported),
        msg_contents: TX_BODY
    }
The server (us) should respond with:
    {
        msg_type: PROCESSED
    }

(we dont have any failure messages right now)


CLIENT_SIDE:
At an undetermined future point in time, the we should respond with:
    {
        msg_type: BLK,
        msg_contents: BLK_BODY
    }

where BLK_BODY, is a very simplified block (no state validation or anything):
    {
        txs: [TX_HASH_LIST]
    }
    
At which point the other client should respond with:
    {
        msg_type: PROCESSED
    }
'''
class MsgProcessor():
    def __init__(self, conn = ('127.0.0.1', 30302), serv_conn = ('127.0.0.1', 30303)):
        self.worker = None
        self.shutdown = False
        self.conn = conn
        self.serv_conn = serv_conn
        self.q = Queue()

    '''
    Runs the message processor, no lightweight threads are started until this point
    '''
    def run(self):
        self._run()


    def _run(self):
        sock_serv = None
        sock = None

        # defines the server connection routine
        def serve_connect():
            global sock_serv
            sock_serv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_serv.bind(self.serv_conn)
            print("MsgProcessor socket server bound")

        # defines the client connection routine
        def client_connect():
            global sock
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(self.conn)
            print("MsgProcessor socket client connected")

        g_lst = [Greenlet(serve_connect).start(), Greenlet(client_connect).start()]
        gevent.joinall(g_lst)

    def send_block(self, tx_list):
        self.q.put(json.dumps({'msg_type': 'BLK', 'tx_list': [base64.b64encode(tx_list)]}))

    def stop(self):
        self.shutdown = True