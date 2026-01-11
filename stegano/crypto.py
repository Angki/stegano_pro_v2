from __future__ import annotations
import hashlib
from typing import Optional

# cryptography is optional unless encryption is requested
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
except Exception:
    AESGCM = None  # type: ignore

def aes_gcm_encrypt(key: bytes, plaintext: bytes, aad: bytes = b'') -> bytes:
    if AESGCM is None:
        raise RuntimeError('cryptography is required for encryption. pip install cryptography')
    if len(key) not in (16, 24, 32):
        raise ValueError('AES-GCM key must be 16, 24, or 32 bytes')
    import os as _os
    nonce = _os.urandom(12)
    aes = AESGCM(key)
    ct = aes.encrypt(nonce, plaintext, aad)
    return b'AGCM' + len(nonce).to_bytes(1, 'big') + nonce + ct


def aes_gcm_decrypt(key: bytes, blob: bytes, aad: bytes = b'') -> bytes:
    if AESGCM is None:
        raise RuntimeError('cryptography is required for decryption. pip install cryptography')
    if not blob.startswith(b'AGCM'):
        raise ValueError('Invalid encrypted blob header')
    ln = blob[4]
    nonce = blob[5:5+ln]
    ct = blob[5+ln:]
    aes = AESGCM(key)
    return aes.decrypt(nonce, ct, aad)

def maybe_encrypt(data: bytes, use_enc: bool, pass_env: Optional[str], pass_str: Optional[str]) -> Tuple[bytes, Optional[str]]:
    if not use_enc:
        return data, None
    key: Optional[bytes] = None
    if pass_env:
        val = os.getenv(pass_env)
        if not val:
            raise RuntimeError(f'Env var {pass_env} not set for encryption')
        key = hashlib.sha256(val.encode('utf-8')).digest()
    elif pass_str:
        key = hashlib.sha256(pass_str.encode('utf-8')).digest()
    else:
        raise RuntimeError('Encryption requested but no password provided')
    enc = aes_gcm_encrypt(key, data, aad=b'stegano_v2')
    return enc, 'aes-256-gcm'


def maybe_decrypt(data: bytes, enc_method: Optional[str], pass_env: Optional[str], pass_str: Optional[str]) -> bytes:
    if not enc_method:
        return data
    if enc_method != 'aes-256-gcm':
        raise RuntimeError(f'Unsupported encryption method {enc_method}')
    if pass_env:
        val = os.getenv(pass_env)
        if not val:
            raise RuntimeError(f'Env var {pass_env} not set for decryption')
        key = hashlib.sha256(val.encode('utf-8')).digest()
    elif pass_str:
        key = hashlib.sha256(pass_str.encode('utf-8')).digest()
    else:
        raise RuntimeError('Decryption password not supplied')
    return aes_gcm_decrypt(key, data, aad=b'stegano_v2')
