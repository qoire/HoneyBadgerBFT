import gevent
from gevent.event import Event
from gevent.queue import Queue
from honeybadgerbft.core.commoncoin import shared_coin
from honeybadgerbft.core.binaryagreement import binaryagreement
from honeybadgerbft.core.reliablebroadcast import reliablebroadcast
from honeybadgerbft.core.commonsubset import commonsubset
from honeybadgerbft.core.honeybadger_block import honeybadger_block
from honeybadgerbft.crypto.threshenc import tpke

class HoneyBadgerBFT():

    def __init__(self, sid, pid, B, N, f, sPK, sSK, ePK, eSK, send, recv, ob, run_forever = False):
        """
        Initializes the HoneyBadgerBFT class, technically this class takes input transactions
        and returns blocks, in our case blocks are returned through the ob function
        :param sid: session id
        :param pid: process id (has correlation with the parameter index of tpke)
        :param B:
        :param N:
        :param f:
        :param sPK: signature public key (boldyreva)
        :param sSK: signature secret key (boldyreva)
        :param ePK: encryption public key (tpke)
        :param eSK: encryption secret key (tpke)
        :param send: function to send a message to an external actor
        :param recv: function to receive a message from external actor
        :param ob: unary function that takes a transaction (hash) as input
        :param run_forever: a boolean parameter specifying whether to run forever
        """
        self.sid = sid
        self.pid = pid
        self.B = B
        self.N = N
        self.f = f
        self.sPK = sPK
        self.sSK = sSK
        self.ePK = ePK
        self.eSK = eSK
        self._send = send
        self._recv = recv
        self.run_forever = run_forever
        self.step = -1

        # ob is a function that passes the block to an outbound
        self.ob = ob

        self.round = 0  # Current block number
        self.transaction_buffer = []
        self._per_round_recv = {}  # Buffer of incoming messages
        print("initialized Badger with pid {}".format(self.pid))


    def submit_tx(self, tx):
        print 'submit_tx', self.pid, tx
        self.transaction_buffer.append(tx)

    def maxsteps(self, steps):
        """
        Sets the amount of steps the consensus is able to run
        by "steps" we mean the amount of rounds
        :param steps:
        :return:
        """
        self.step = steps

    def run(self):
        def _recv():
            while True:
                (sender, (r, msg)) = self._recv()
            
                # Maintain an *unbounded* recv queue for each epoch
                if r not in self._per_round_recv:
                    # Buffer this message
                    assert r >= round
                    self._per_round_recv[r] = Queue()

                _recv = self._per_round_recv[r]
                if _recv is None:
                    # We have already closed this
                    # round and will stop participating!
                    pass
                else:
                    # Queue it
                    _recv.put( (sender, msg) )
        self._recv_thread = gevent.spawn(_recv)

        while True:
            # first check if we can still operate, otherwise just loop
            if self.step != -1 and self.step <= 0:
                gevent.sleep(0.1) # yield and sleep
                continue

            print("pid {}, starting next round, currently at {} steps".format(self.pid, self.step))

            # For each round...
            r = self.round
            if r not in self._per_round_recv:
                self._per_round_recv[r] = Queue()

            # Select all the transactions (TODO: actual random selection)
            tx_to_send = self.transaction_buffer[:self.B]

            # TODO: Wait a bit if transaction buffer is not full

            # Run the round
            def _make_send(r):
                def _send(j, o):
                    self._send(j, (r, o))
                return _send
            send_r = _make_send(r)
            recv_r = self._per_round_recv[r].get

            tx = None
            if len(tx_to_send) > 0:
                tx = tx_to_send[0]

            if tx == None:
                tx = "00"

            new_tx = self._run_round(r, tx, send_r, recv_r)
            print 'pid:', self.pid, ' new_tx:', new_tx
            self.ob(new_tx)

            # Remove all of the new transactions from the buffer
            self.transaction_buffer = [_tx for _tx in self.transaction_buffer if _tx not in new_tx]

            self.round += 1 # Increment the round

            if (self.step != -1):
                self.step = self.step - 1

            if not self.run_forever:
                if self.round >= 3: break # Only run one round for now


    def _run_round(self, r, tx_to_send, send, recv):
        # Unique sid for each round
        sid = self.sid + ':' + str(r)
        pid = self.pid
        N = self.N
        f = self.f

        def broadcast(o):
            for j in range(N): send(j, o)

        # Launch ACS, ABA, instances
        coin_recvs = [None] * N
        aba_recvs  = [None] * N
        rbc_recvs  = [None] * N

        aba_inputs  = [Queue(1) for _ in range(N)]
        aba_outputs = [Queue(1) for _ in range(N)]
        rbc_outputs = [Queue(1) for _ in range(N)]

        my_rbc_input = Queue(1)
        print pid, r, 'tx_to_send:', tx_to_send

        def _setup(j):
            def coin_bcast(o):
                broadcast(('ACS_COIN', j, o))

            coin_recvs[j] = Queue()
            coin = shared_coin(sid + 'COIN' + str(j), pid, N, f,
                               self.sPK, self.sSK,
                               coin_bcast, coin_recvs[j].get)

            def aba_bcast(o):
                broadcast(('ACS_ABA', j, o))

            aba_recvs[j] = Queue()
            aba = gevent.spawn(binaryagreement, sid+'ABA'+str(j), pid, N, f, coin,
                               aba_inputs[j].get, aba_outputs[j].put_nowait,
                               aba_bcast, aba_recvs[j].get)

            def rbc_send(k, o):
                send(k, ('ACS_RBC', j, o))

            # Only leader gets input
            rbc_input = my_rbc_input.get if j == pid else None
            rbc_recvs[j] = Queue()
            rbc = gevent.spawn(reliablebroadcast, sid+'RBC'+str(j), pid, N, f, j,
                               rbc_input, rbc_recvs[j].get, rbc_send)
            rbc_outputs[j] = rbc.get  # block for output from rbc

        # N instances of ABA, RBC
        for j in range(N): _setup(j)

        # One instance of TPKE
        def tpke_bcast(o):
            broadcast(('TPKE', 0, o))

        tpke_recv = Queue()

        # One instance of ACS
        acs = gevent.spawn(commonsubset, pid, N, f, rbc_outputs,
                           [_.put_nowait for _ in aba_inputs],
                           [_.get for _ in aba_outputs])
        
        def _recv():
            while True:
                (sender, (tag, j, msg)) = recv()
                if   tag == 'ACS_COIN': coin_recvs[j].put_nowait((sender,msg))
                elif tag == 'ACS_RBC' : rbc_recvs [j].put_nowait((sender,msg))
                elif tag == 'ACS_ABA' : aba_recvs [j].put_nowait((sender,msg))
                elif tag == 'TPKE'    : tpke_recv.put_nowait((sender,msg))
                else:
                    print 'Unknown tag!!', tag
                    raise
        gevent.spawn(_recv)

        _input = Queue(1)
        _input.put(tx_to_send)
        return honeybadger_block(pid, self.N, self.f, self.ePK,self. eSK,
                                 _input.get,
                                 acs_in=my_rbc_input.put_nowait, acs_out=acs.get,
                                 tpke_bcast=tpke_bcast, tpke_recv=tpke_recv.get)
