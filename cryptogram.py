import base64
import re
import secrets


class RSA:
    def __init__(self, byte_order='big'):
        self.byte_order = byte_order
        self.N = 0
        self.E = 0
        self.N_bytes_length = 0  # N bytes length

    def set_public_key(self, modulus: bytes, exponent: bytes = b'\x01\x00\x01') -> None:
        """
        Set the public key, include modulus and exponent
        """

        self.N = int.from_bytes(modulus, self.byte_order)
        self.E = int.from_bytes(exponent, self.byte_order)
        self.N_bytes_length = (self.N.bit_length() + 7) >> 3
        return

    def _padding_zero(self, bytes_text: bytes, reverse: bool = False) -> bytes:
        padding_length = self.N_bytes_length - len(bytes_text)
        if padding_length <= 0:
            raise ValueError("Text is too long")
        else:
            bytes_text = b'\x00'*padding_length + (reversed(bytes_text) if reverse else bytes_text)
            return bytes_text

    def _padding_pkcs1_private(self, bytes_text: bytes) -> bytes:
        padding_length = self.N_bytes_length - len(bytes_text) - 3
        if padding_length < 8:
            raise ValueError("Text is too long")
        else:
            padding_bytes = b'\xff'*padding_length
            bytes_text = b'\x00\x01' + padding_bytes + b'\x00' + bytes_text
            return bytes_text

    def _padding_pkcs1_public(self, bytes_text: bytes) -> bytes:
        padding_length = self.N_bytes_length - len(bytes_text) - 3
        if padding_length < 8:
            raise ValueError("Text is too long")
        else:
            # non zero padding
            padding_bytes = secrets.token_bytes(padding_length).replace(b'\x00', b'\xcc')
            bytes_text = b'\x00\x02' + padding_bytes + b'\x00' + bytes_text
            return bytes_text

    def encrypt(self, plain_text: bytes, padding_type) -> bytes:
        """
        RSA encrypt

        params:
            plain_text: text to encrypt
            padding_type: can be 'zero', 'zero_reverse', 'pkcs1_1', 'pkcs1_2'
                zero: || 0x00 ... 0x00 || plain_text ||
                zero_reverse: || 0x00 ... 0x00 || reverse(plain_text) ||
                pkcs1_1: || 0x00 || 0x01 || 0xff ... 0xff || 0x00 || plain_text ||
                pkcs1_2: || 0x00 || 0x02 || rand_byte ... rand_byte || 0x00 || plain_text ||

                or can be a function: 
                    param: bytes 
                    return: bytes

        returns:
            encrypted text
        """

        # padding
        if isinstance(padding_type, str):
            if padding_type == 'zero':
                padding_text = self._padding_zero(plain_text)
            elif padding_type == 'zero_reverse':
                padding_text = self._padding_zero(plain_text, True)
            elif padding_type == 'pkcs1_1':
                padding_text = self._padding_pkcs1_private(plain_text)
            elif padding_type == 'pkcs1_2':
                padding_text = self._padding_pkcs1_public(plain_text)
            else:
                raise ValueError(f"Invalid padding type: {padding_type}")
        elif callable(padding_type):
            padding_text = padding_type(plain_text)
        else:
            raise TypeError(f"Invalid padding type: {type(padding_type)}")

        # encrypt
        cipher_text = int.from_bytes(padding_text, self.byte_order)
        cipher_text = pow(cipher_text, self.E, self.N)  # type: int
        cipher_text = cipher_text.to_bytes(self.N_bytes_length, self.byte_order)

        return cipher_text

    def decrypt(self, cipher_text: bytes) -> bytes:
        ...


class RC4:
    """
    RC4 stream cryptor
    """
    def __init__(self):
        self.key = None
        self.table_R = None
        self.table_S = None
        self.S_I = 0
        self.S_J = 0

    def set_key(self, key: bytes):
        """
        first use this method to set a key,
        when called, it will auto invoke self.init_state() to initiate the state

        params:
            key: used fo encrypt and decrypt
        """

        self.key = key
        self.table_R = []

        for i in range(256):
            self.table_R.append(self.key[i % len(self.key)])

        self.init_state()

    def init_state(self):
        """
        initiate the state

        this method will initiate the S table S_I and S_J point,
        you may call this method when you need to encrypt/decrypt a new message
        """

        self.S_I = self.S_J = 0
        self.table_S = list(range(256))

        j = 0
        for i in range(256):
            j = (j + self.table_S[i] + self.table_R[i]) % 256
            self.table_S[i], self.table_S[j] = self.table_S[j], self.table_S[i]

    def encrypt(self, plain_text):
        """
        RC4 encrypt

        params:
            cipher_text: message to decrypt, can be bytes or bytes iterator
        """
        return bytes(self._crypt(plain_text))

    def decrypt(self, cipher_text):
        """
        RC4 decrypt

        params:
            cipher_text: message to decrypt, can be bytes or bytes iterator
        """
        return bytes(self._crypt(cipher_text))

    def _crypt(self, bytes_text: bytes):
        for byte in bytes_text:
            self.S_I = (self.S_I + 1) % 256
            self.S_J = (self.S_J + self.table_S[self.S_I]) % 256
            self.table_S[self.S_I], self.table_S[self.S_J] = self.table_S[self.S_J], self.table_S[self.S_I]
            k = self.table_S[(self.table_S[self.S_I] + self.table_S[self.S_J]) % 256]
            yield (byte ^ k)
