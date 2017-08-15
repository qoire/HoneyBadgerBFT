import gevent
import json
import zmq.green as zmq
import base64
from Queue import Queue
from gevent import Greenlet
from gevent import monkey
monkey.patch_all()

class PoisonPill:
    '''
    To kill the necessary threads
    '''
    def __init__(self):
        pass

class MsgProcessor():
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
            @type: connect
            host: '127.0.0.1'
            port: 30303 (or something like that)
        }

    3) At which point we assume the other side has connected to us, proceed as usual

    SERVER_SIDE:
    Messages should be in the following format:
        {
            @type: tx_msg (so far only transaction messages supported),
            msg_contents: TX_BODY
        }

    (we dont have any failure messages right now)


    CLIENT_SIDE:
    At an undetermined future point in time, the we should respond with:
        {
            @type: blk_msg,
            msg_contents: [tx_hash, ...]
        }
    '''
    MSG_SIZE = 4096

    def __init__(self, conn = ('127.0.0.1', 30302), serv_conn = ('127.0.0.1', 30303)):
        self.worker = None
        self.shutdown = False
        self.conn = conn
        self.serv_conn = serv_conn
        self.q = Queue()

        self.server_shutdown = False
        self.client_shutdown = False

        self.server_t = None
        self.client_t = None

        self.out = None

        self.t = None


    def run(self):
        '''
        Runs the message processor, no lightweight threads are started until this point
        '''
        if self.t != None:
            return

        self.t = Greenlet(self._run).start()


    def _run(self):
        '''
        TODO: add exception handling
        '''
        self.context = zmq.Context()

        def _server():
            print("MsgProcessor: server running")
            socket = self.context.socket(zmq.PAIR)
            socket.bind("tcp://127.0.0.1:%s" % self.serv_conn[1])
            print("MsgProcessor: server -> bound to tcp://127.0.0.1:{}".format(self.serv_conn[1]))
            return socket

        def _client():
            print("MsgProcessor: client running")
            socket = self.context.socket(zmq.PAIR)
            socket.connect("tcp://localhost:%s" % self.conn[1])
            print("MsgProcessor: client -> connection established")
            return socket


        g_s = Greenlet.spawn(_server)
        g_c = Greenlet.spawn(_client)
        ret = gevent.joinall([g_s, g_c])
        client_sock = ret[1].value

        # lets also bind to class
        self.server_sock = ret[0].value # type: zmq.socket
        self.client_sock = ret[1].value # type: zmq.socket

        # now all connections are established, run the routines
        print("MsgProcessor: connection, established, sending counterparty information")
        client_sock.send(json.dumps({'@type': 'connect_msg', 'host': '127.0.0.1', 'port': 30303}))

        self.server_t = Greenlet(self._client)
        self.client_t = Greenlet(self._server)

        self.server_t.start()
        self.client_t.start()


    def _client(self):
        '''
        Client routine, defines an inbound queue (from our perspective),
        the only message that we support currently is BLK
        '''

        client = self.client_sock

        if client == None:
            raise RuntimeError("client_sock not connected")

        print("MsgProcessor: client (us -> kernel) subroutine active")

        while not self.client_shutdown:
            msg = self.q.get()

            if isinstance(msg, PoisonPill):
                break

            # expecting a dictionary here thats serializable
            client.send(json.dumps(msg))

        print("MsgProcessor: client shutdown")


    def _server(self):
        '''
        Server routine, defines an outbound queue, directly triggers
        '''
        server = self.server_sock

        if server == None:
            raise RuntimeError("server_sock not connected")

        print ("MsgProcessor: server (kernel -> us) subroutine active")

        while not self.server_shutdown:
            msg = server.get()
            obj = json.loads(msg)

            if (obj['msg_type'] == 'DISCONNECT'):
                # we're being disconnected, send poison pill to client and disconnect
                self.q.put(PoisonPill())
                break
            elif (obj['msg_type'] == 'TX'):
                tx_hash = obj['tx_hash'] # expected 32-byte hash

                # only send message if we've already hooked up the outbound connection
                if not self.out == None:
                    self.out(tx_hash)

        print("MsgProcessor: server shutdown")

    def hookup(self, out):
        """
        :param out: a function that accepts the transaction into the system
        :return:
        """
        self.out = out


    def send_block(self, tx_list, binary=False):
        if binary:
            tx_list = [a.encode('hex_codec') for a in tx_list]
        self.q.put(json.dumps({'@type': 'blk_msg', 'tx_list': tx_list}))

    def block(self):
        # block, dirty, used to block the main thread
        gevent.joinall(self.t)

    def stop(self):
        self.server_shutdown = True
        self.client_shutdown = True

        gevent.joinall([self.server_t, self.client_t])

        if self.server_sock != None:
            self.server_sock.close()

        if self.client_sock != None:
            self.client_sock.close()

        if self.context != None:
            self.context.term()