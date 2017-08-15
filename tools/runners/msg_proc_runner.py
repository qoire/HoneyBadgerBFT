# Runner for running network_node_test.py
# Lets us get around PyCharms limitations around pythons module system
from MsgProcessor import MsgProcessor

import time

def main():
    proc = MsgProcessor()
    proc.run()
    time.sleep(100000000)

if __name__ == '__main__':
    main()