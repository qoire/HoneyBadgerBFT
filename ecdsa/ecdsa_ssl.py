# -*- Mode: Python -*-

# OpenSSL wrapper, from
# https://github.com/joric/brutus/blob/master/ecdsa_ssl.py

import ctypes
import ctypes.util
import platform

ssl = ctypes.cdll.LoadLibrary (ctypes.util.find_library ('ssl') or 'libeay32')

# this specifies the curve used with ECDSA.
NID_secp256k1 = 714 # from openssl/obj_mac.h

# Thx to Sam Devlin for the ctypes magic 64-bit fix.
def check_result (val, func, args):
    if val == 0:
        raise ValueError
    else:
        return ctypes.c_void_p (val)

if platform.architecture()[0] == "64bit":
    # BN (BigNumber) related
    # bn/bn.h int           BN_bn2bin(const BIGNUM *a, unsigned char *to)
    ssl.BN_bn2bin.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ssl.BN_bn2bin.restype = ctypes.c_int

    # bn/bn.h BIGNUM        *BN_new(void)
    ssl.BN_new.argtypes = []
    ssl.BN_new.restype = ctypes.c_void_p
    ssl.BN_new.errcheck = check_result

    # bn/bn.h BN_CTX        *BN_CTX_new(void)
    ssl.BN_CTX_new.argtypes = []
    ssl.BN_CTX_new.restype = ctypes.c_void_p
    ssl.BN_new.errcheck = check_result

    # bn/bn.h void          BN_CTX_free(BN_CTX *c)
    ssl.BN_CTX_free.argtypes = [ctypes.c_void_p]
    # void

    # ECKEY related
    # bn/bn.h               EC_KEY_new_by_curve_name(const *)
    ssl.EC_KEY_new_by_curve_name.argtypes = [ctypes.c_int]
    ssl.EC_KEY_new_by_curve_name.restype = ctypes.c_void_p

    ssl.EC_KEY_get0_private_key.argtypes = [ctypes.c_void_p]
    ssl.EC_KEY_get0_private_key.restype = ctypes.c_void_p

    # ec/ec.h EC_GROUP      *EC_KEY_get0_group(const EC_KEY *key)
    ssl.EC_KEY_get0_group.argtypes = [ctypes.c_void_p]
    ssl.EC_KEY_get0_group.restype = ctypes.c_void_p

    # ec/ec.h EC_POINT      *EC_POINT_new(const EC_GROUP *group)
    ssl.EC_POINT_new.argtypes = [ctypes.c_void_p]
    ssl.EC_POINT_new.restype = ctypes.c_void_p

    #                       EC_KEY_set_private_key
    ssl.EC_KEY_set_private_key.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ssl.EC_KEY_set_private_key.restype = ctypes.c_int

    #                       EC_KEY_set_public_key
    ssl.EC_KEY_set_public_key.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ssl.EC_KEY_set_public_key.restype = ctypes.c_int

    # ec/ec_lib.c void      EC_POINT_free(EC_POINT *point)
    ssl.EC_POINT_free.argtypes = [ctypes.c_void_p]
    # void - no return type

    #                       EC_KEY_generate_key
    ssl.EC_KEY_generate_key.argtypes = [ctypes.c_void_p]
    ssl.EC_KEY_generate_key.restype = ctypes.c_int

    # ec/ec.h               d2i_ECPrivateKey
    ssl.d2i_ECPrivateKey.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
    ssl.d2i_ECPrivateKey.restype = ctypes.c_void_p


    # ec/ec.h EC_KEY        *o2i_ECPublicKey(EC_KEY **a, const unsigned char **in, long len)
    ssl.o2i_ECPublicKey.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
    ssl.o2i_ECPublicKey.restype = ctypes.c_void_p

    # ec/ec.h int           i2d_ECPrivateKey(EC_KEY *key, unsigned char **out)
    ssl.i2d_ECPrivateKey.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ssl.i2d_ECPrivateKey.restype = ctypes.c_int

    # ec/ec.h EC_KEY        *i2o_ECPublicKey(EC_KEY **key, const unsigned char **in, long len)
    ssl.i2o_ECPublicKey.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
    ssl.i2o_ECPublicKey.restype = ctypes.c_void_p

    # ecdsa/ecdsa.h int     ECDSA_size(const EC_KEY *eckey)
    ssl.ECDSA_size.argtypes = [ctypes.c_void_p]
    ssl.ECDSA_size.restype = ctypes.c_int

    # ecdsa/ecdsa.h int     ECDSA_sign(int type, const unsigned char *dgst, int dgstlen,
    #                               unsigned char *sig, unsigned int *siglen, EC_KEY *eckey))
    ssl.ECDSA_sign.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
                               ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
    ssl.ECDSA_sign.restype = ctypes.c_int

    # ecdsa/ecdsa.h         ECDSA_verify(int type, const unsigned char *dgst, int dgst_len,
    #                               const unsigned char *sigbuf, int sig_len, EC_KEY *eckey)
    ssl.ECDSA_verify.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int,
                                 ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]

class KEY:

    def __init__(self):
        self.POINT_CONVERSION_COMPRESSED = 2
        self.POINT_CONVERSION_UNCOMPRESSED = 4
        self.k = ssl.EC_KEY_new_by_curve_name(NID_secp256k1)

    def __del__(self):
        if ssl:
            ssl.EC_KEY_free(self.k)
        self.k = None

    def generate(self, secret=None):
        if secret:
            self.prikey = secret
            priv_key = ssl.BN_bin2bn(secret, 32, ssl.BN_new())
            group = ssl.EC_KEY_get0_group(self.k)
            pub_key = ssl.EC_POINT_new(group)
            ctx = ssl.BN_CTX_new()
            ssl.EC_POINT_mul(group, pub_key, priv_key, None, None, ctx)
            ssl.EC_KEY_set_private_key(self.k, priv_key)
            ssl.EC_KEY_set_public_key(self.k, pub_key)
            ssl.EC_POINT_free(pub_key)
            ssl.BN_CTX_free(ctx)
            return self.k
        else:
            return ssl.EC_KEY_generate_key(self.k)

    def set_privkey(self, key):
        self.mb = ctypes.create_string_buffer(key)
        ssl.d2i_ECPrivateKey(ctypes.byref(self.k), ctypes.byref(ctypes.pointer(self.mb)), len(key))

    def set_pubkey(self, key):
        self.mb = ctypes.create_string_buffer(key)
        ssl.o2i_ECPublicKey(ctypes.byref(self.k), ctypes.byref(ctypes.pointer(self.mb)), len(key))

    def get_privkey(self):
        size = ssl.i2d_ECPrivateKey(self.k, 0)
        mb_pri = ctypes.create_string_buffer(size)
        ssl.i2d_ECPrivateKey(self.k, ctypes.byref(ctypes.pointer(mb_pri)))
        return mb_pri.raw

    def get_pubkey(self):
        size = ssl.i2o_ECPublicKey(self.k, 0)
        mb = ctypes.create_string_buffer(size)
        ssl.i2o_ECPublicKey(self.k, ctypes.byref(ctypes.pointer(mb)))
        return mb.raw

    def sign(self, hash):
        sig_size = ssl.ECDSA_size(self.k)
        mb_sig = ctypes.create_string_buffer(sig_size)
        sig_size0 = ctypes.c_uint32()
        assert 1 == ssl.ECDSA_sign(0, hash, len(hash), mb_sig, ctypes.byref(sig_size0), self.k)
        return mb_sig.raw[:sig_size0.value]

    def verify(self, hash, sig):
        return ssl.ECDSA_verify(0, hash, len(hash), sig, len(sig), self.k)

    def set_compressed(self, compressed):
        if compressed:
            form = self.POINT_CONVERSION_COMPRESSED
        else:
            form = self.POINT_CONVERSION_UNCOMPRESSED
        ssl.EC_KEY_set_conv_form(self.k, form)


    def get_secret(self):
        bn = ssl.EC_KEY_get0_private_key(self.k)
        mb = ctypes.create_string_buffer(32)
        ssl.BN_bn2bin(bn, mb)
        return mb.raw