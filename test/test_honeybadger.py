import unittest
import gevent
import random
from gevent.event import Event
from gevent.queue import Queue
import honeybadgerbft.core.honeybadger
reload(honeybadgerbft.core.honeybadger)
from honeybadgerbft.core.honeybadger import HoneyBadgerBFT
from honeybadgerbft.crypto.threshsig.boldyreva import dealer
from honeybadgerbft.crypto.threshenc import tpke
from collections import defaultdict

def simple_router(N, maxdelay=0.005, seed=None):
    """Builds a set of connected channels, with random delay
    @return (receives, sends)
    """
    rnd = random.Random(seed)
    #if seed is not None: print 'ROUTER SEED: %f' % (seed,)
    
    queues = [Queue() for _ in range(N)]
    _threads = []

    def makeSend(i):
        def _send(j, o):
            delay = rnd.random() * maxdelay
            #delay = 0.1
            #print 'SEND   %8s [%2d -> %2d] %2.1f' % (o[0], i, j, delay*1000), o[1:]
            gevent.spawn_later(delay, queues[j].put_nowait, (i,o))
        return _send

    def makeRecv(j):
        def _recv():
            (i,o) = queues[j].get()
            # print 'RECV %8s [%2d -> %2d]' % (o[0], i, j)
            return (i,o)
        return _recv
        
    return ([makeSend(i) for i in range(N)],
            [makeRecv(j) for j in range(N)])


def _setup_badgers(N=4, f=1, seed=None, steps = -1):
    """
    Setups up badgers in a fake network with queue based network.
    Also, new keys are generated time the network is booted up, but
    the ecdsa key should remain constant
    :param N:
    :param f:
    :param seed:
    :return:
    """
    sid = 'sidA'
    # Generate threshold sig keys
    sPK, sSKs = dealer(N, f + 1, seed=seed)
    # Generate threshold enc keys
    ePK, eSKs = tpke.dealer(N, f + 1)

    rnd = random.Random(seed)
    # print 'SEED:', seed
    router_seed = rnd.random()
    sends, recvs = simple_router(N, maxdelay= 0, seed=router_seed)

    def outbound(tx):
        pass

    run_forever = False

    badgers = [None] * N
    threads = [None] * N
    for i in range(N):
        badgers[i] = HoneyBadgerBFT(sid, i, 1, N, f,
                                    sPK, sSKs[i], ePK, eSKs[i],
                                    sends[i], recvs[i], outbound, run_forever)
        badgers[i].maxsteps(steps)
        threads[i] = gevent.spawn(badgers[i].run)

    return threads, badgers


### Test asynchronous common subset
def _test_honeybadger(N=4, f=1, seed=None):
    threads, badgers = _setup_badgers(N, f)

    for i in range(N):
        #if i == 1: continue
        badgers[i].submit_tx('<[HBBFT Input %d]>' % i)

    for i in range(N):
        badgers[i].submit_tx('<[HBBFT Input %d]>' % (i+10))

    for i in range(N):
        badgers[i].submit_tx('<[HBBFT Input %d]>' % (i+20))
        
    #gevent.killall(threads[N-f:])
    #gevent.sleep(3)
    #for i in range(N-f, N):
    #    inputs[i].put(0)
    try:
        outs = [threads[i].get() for i in range(N)]

        # Consistency check
        assert len(set(outs)) == 1
        
    except KeyboardInterrupt:
        gevent.killall(threads)
        raise

def _test_honeybadger_single_tx(N=4, f=1, seed=None):
    threads, badgers = _setup_badgers(N, f)
    badgers[0].submit_tx('<HBBFT Input 0>')
    badgers[0].submit_tx('<HBBFT Input 1>')
    badgers[0].submit_tx('<HBBFT Input 2>')

    try:
        outs = [threads[i].get() for i in range(N)]

        # Consistency check
        assert len(set(outs)) == 1

    except KeyboardInterrupt:
        gevent.killall(threads)
        raise

def _test_honeybadger_no_tx(N=4, f=1, seed=None):
    threads, badgers = _setup_badgers(N, f)

    try:
        outs = [threads[i].get() for i in range(N)]

        # Consistency check
        assert len(set(outs)) == 1

    except KeyboardInterrupt:
        gevent.killall(threads)
        raise

def _test_honeybadger_yielding(N=4, f=1, seed=None):
    threads, badgers = _setup_badgers(N, f, steps=0)
    try:
        outs = [threads[i].get() for i in range(N)]

        # Consistency check
        assert len(set(outs)) == 1

    except KeyboardInterrupt:
        gevent.killall(threads)
        raise


from nose2.tools import params

def test_honeybadger():
    # _test_honeybadger()
    # _test_honeybadger_single_tx()
    # _test_honeybadger_no_tx()
    _test_honeybadger_yielding()

# if we want to run it in pycharm instead
if __name__ == '__main__':
    test_honeybadger()

