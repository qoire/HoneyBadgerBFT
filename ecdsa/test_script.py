# test script for checking if openssl is working

import ctypes
import ctypes.util

ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl') or 'libeay32')
NID_secp256k1 = 714 # from openssl/obj_mac.h

ssl.EC_KEY_new_by_curve_name.argtypes = [ctypes.c_int]
ssl.EC_KEY_new_by_curve_name.restype = ctypes.c_void_p

ssl.BN_value_one.restype = ctypes.c_void_p

ssl.BN_num_bits.argtypes = [ctypes.c_void_p]


class BIGNUM(ctypes.Structure):
    """ creates a struct to match BIGNUM on bn/bn.h side """

    _fields_ = [
        ('d', ctypes.POINTER(ctypes.c_ulonglong)),
        ('top', ctypes.c_int),
        ('dmax', ctypes.c_int),
        ('neg', ctypes.c_int),
        ('flags', ctypes.c_int)
    ]


class TestClass:
    def __init__(self):
        self.k = ssl.EC_KEY_new_by_curve_name(NID_secp256k1)
        self.bn = ssl.BN_value_one()
        pass

    def run(self):
        ssl.BN_num_bits(self.bn)


def main():
    t = TestClass()
    t.run()

if __name__ == '__main__':
    main()