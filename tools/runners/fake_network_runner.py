# Initializes a fake network runner
# Similar to test_honeybadger.py
# Emulates randomly varying channels

from MsgProcessor import MsgProcessor
import random
from Queue import Queue
import gevent
from honeybadgerbft.crypto.threshsig.boldyreva import dealer
from honeybadgerbft.crypto.threshenc import tpke
from honeybadgerbft.core.honeybadger import HoneyBadgerBFT
import signal

def tx_input_router(badgers):
    """
    Generates a transaction input router, that routes messages between the input
    and N different outputs, allows us to easily swap this out for
    a different implementation later
    :param N:
    :return:
    """
    rnd = random.Random(314159) # arbitrary

    def _send(tx):
        r = rnd.randint(0, len(badgers)-1)
        badgers[r].submit(tx)

    return _send


def simple_router(N, maxdelay=0.005, seed=None):
    """Builds a set of connected channels, with random delay
    @return (receives, sends)
    """
    rnd = random.Random(seed)
    # if seed is not None: print 'ROUTER SEED: %f' % (seed,)

    queues = [Queue() for _ in range(N)]
    _threads = []

    def makeSend(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            # delay = 0.1
            print 'SEND   %8s [%2d -> %2d] %2.1f' % (o[0], i, j, delay*1000), o[1:]
            gevent.spawn_later(delay, queues[j].put_nowait, (i, o))

        return _send

    def makeRecv(j):
        def _recv():
            (i, o) = queues[j].get()
            # print 'RECV %8s [%2d -> %2d]' % (o[0], i, j)
            return (i, o)

        return _recv

    return ([makeSend(i) for i in range(N)],
            [makeRecv(j) for j in range(N)])

def _setup_badgers(N=4, f=1, seed=None):
    sid = 'mt1'
    # Generate threshold sig keys
    sPK, sSKs = dealer(N, f + 1, seed=seed)
    # Generate threshold enc keys
    ePK, eSKs = tpke.dealer(N, f + 1)

    rnd = random.Random(seed)
    # print 'SEED:', seed
    router_seed = rnd.random()
    sends, recvs = simple_router(N, 0)

    # block output router, routes output blocks
    # TODO: complete when integrating with connecting network
    def route_to_msgproc(tx):
        pass


    badgers = [None] * N
    threads = [None] * N
    for i in range(N):
        badgers[i] = HoneyBadgerBFT(sid, i, 1, N, f,
                                    sPK, sSKs[i], ePK, eSKs[i],
                                    sends[i], recvs[i], route_to_msgproc, True)
        threads[i] = gevent.spawn(badgers[i].run)
    return threads, badgers


def _hookup_msg_processor(proc, b):
    """
    Hooks up the message processor to the badgers
    :param proc:
    :param b:
    :return:
    """
    send_fn = tx_input_router(b)
    proc.hookup(send_fn)

def setup_network(n):
    # deal threshold signatures
    sPK, sSKs = dealer(4, 2) # n, f+1
    ePK, eSKs = tpke.dealer(4, 2)
    t, b = _setup_badgers(4, 2, 0)
    proc = MsgProcessor()
    _hookup_msg_processor(proc, b)
    proc.run()

    try:
        proc.block()
    except KeyboardInterrupt:
        gevent.killall(t)
        proc.stop()
        raise


def main():
    setup_network(4)

if __name__ == '__main__':
    main()