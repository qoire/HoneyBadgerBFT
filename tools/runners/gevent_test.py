import unittest
import gevent

class TestGeventThreading(unittest.TestCase):

    def test_debug_threading(self):

        def print_hello_world():
            for i in range(0, 10):
                print("hello world")

        def print_hello_earth():
            for i in range(0, 10):
                print("hello earth")

        t = gevent.spawn(print_hello_world)
        t2 = gevent.spawn(print_hello_earth)
        gevent.joinall([t, t2])