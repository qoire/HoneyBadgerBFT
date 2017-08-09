# Runner for running network_node_test.py
# Lets us get around PyCharms limitations around pythons module system
import sys
import os
from MsgProcessor import MsgProcessor

sys.path.append(os.path.abspath("HoneyBadgerBFT"))
sys.path.append(os.path.abspath(os.path.curdir))

#import HoneyBadgerBFT.test.network_node_test

def main():
    proc = MsgProcessor()
    proc.run()

if __name__ == '__main__':
    main()