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

    def encrypt(self, bytes_text: bytes, padding_type) -> bytes:
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
                padding_text = self._padding_zero(bytes_text)
            elif padding_type == 'zero_reverse':
                padding_text = self._padding_zero(bytes_text, True)
            elif padding_type == 'pkcs1_1':
                padding_text = self._padding_pkcs1_private(bytes_text)
            elif padding_type == 'pkcs1_2':
                padding_text = self._padding_pkcs1_public(bytes_text)
            else:
                raise ValueError(f"Invalid padding type: {padding_type}")
        elif callable(padding_type):
            padding_text = padding_type(bytes_text)
        else:
            raise TypeError(f"Invalid padding type: {type(padding_type)}")

        # encrypt
        cipher_text = int.from_bytes(padding_text, self.byte_order)
        cipher_text = pow(cipher_text, self.E, self.N)  # type: int
        cipher_text = cipher_text.to_bytes(self.N_bytes_length, self.byte_order)

        return cipher_text

    def decrypt(self, bytes_cipher: bytes) -> bytes:
        ...
