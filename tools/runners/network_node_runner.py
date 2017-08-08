# Runner for running network_node_test.py
# Lets us get around PyCharms limitations around pythons module system
import sys
import os

sys.path.append(os.path.abspath("HoneyBadgerBFT"))
sys.path.append(os.path.abspath(os.path.curdir))

import HoneyBadgerBFT.test.network_node_test

def main():
    HoneyBadgerBFT.test.network_node_test.main()

if __name__ == '__main__':
    print
    print(sys.argv)
    main()