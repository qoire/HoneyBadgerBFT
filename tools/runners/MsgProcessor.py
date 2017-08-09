import gevent
import json
import zmq
import base64
from Queue import Queue
from gevent import Greenlet


'''
To kill the necessary threads
'''
class PoisonPill:
    def __init__(self):
        pass

'''
A block, created from a list of transactions (hashes), assumes that
the transactions are encoded in binary format
'''
class Block:
    def __init__(self, txs):
        self.txs = txs

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
'''
class MsgProcessor():
    MSG_SIZE = 4096

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
        Greenlet(self._run()).start()

    '''
    TODO: add exception handling
    '''
    def _run(self):
        context = zmq.Context()

        def _server():
            print("MsgProcessor: server running")
            socket = context.socket(zmq.PAIR)
            socket.bind("tcp://127.0.0.1:%s" % self.serv_conn[1])
            print("MsgProcessor: server -> bound")
            return socket

        def _client():
            print("MsgProcessor: client running")
            socket = context.socket(zmq.PAIR)
            socket.connect("tcp://localhost:%s" % self.conn[1])
            print("MsgProcessor: client -> connection established")
            return socket

        g_s = Greenlet(_server)
        g_c = Greenlet(_client)

        g_s.start()
        g_c.start()

        ret = gevent.joinall([g_s, g_c])
        client_sock = ret[1].value

        # now all connections are established, run the routines
        print("MsgProcessor: connection, established, sending counterparty information")

        def _notify(sock):
            sock.send(json.dumps({'msg_type': 'CONNECT', 'ip': 'localhost', 'port': 30303}))
        Greenlet(_notify, client_sock).start()


    '''
    Client routine, defines an inbound queue (from our perspective),
    the only message that we support currently is BLK
    '''
    def _client(self, socket, iq):
        client = socket
        print("MsgProcessor: client (us -> kernel) routine active")
        while True:
            # expects a json string here, nothing else (exception is poison pill)
            item = iq.get()
            if isinstance(item, PoisonPill):
                break
            client.sendall(item)
        client.shutdown()
        client.close()


    '''
    Server routine, defines an outbound queue, directly triggers
    '''
    def _server(self, socket):
        print("MsgProcessor: server (kernel -> us) routine active")

        while True:
            pass

        socket.shutdown()
        socket.close()

    # expects a list of tx_list in hexstring format
    def send_block(self, tx_list, binary=False):
        if binary:
            tx_list = [a.encode('hex_codec') for a in tx_list]
        self.q.put(json.dumps({'msg_type': 'BLK', 'tx_list': tx_list}))

    def stop(self):
        self.shutdown = True