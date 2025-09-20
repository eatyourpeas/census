from __future__ import annotations

import json
import os
from base64 import urlsafe_b64encode, urlsafe_b64decode
from typing import Tuple
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def derive_key(passphrase: bytes, salt: bytes | None = None) -> Tuple[bytes, bytes]:
    if salt is None:
        salt = os.urandom(16)
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = kdf.derive(passphrase)
    return key, salt


def encrypt_sensitive(passphrase_key: bytes, data: dict) -> bytes:
    key, salt = derive_key(passphrase_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    plaintext = json.dumps(data).encode("utf-8")
    ct = aesgcm.encrypt(nonce, plaintext, None)
    # store salt | nonce | ct
    return salt + nonce + ct


def decrypt_sensitive(passphrase_key: bytes, blob: bytes) -> dict:
    salt, nonce, ct = blob[:16], blob[16:28], blob[28:]
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    key = kdf.derive(passphrase_key)
    aesgcm = AESGCM(key)
    pt = aesgcm.decrypt(nonce, ct, None)
    return json.loads(pt.decode("utf-8"))


def make_key_hash(key: bytes) -> tuple[bytes, bytes]:
    salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
    digest = kdf.derive(key)
    return digest, salt


def verify_key(key: bytes, digest: bytes, salt: bytes) -> bool:
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000)
    try:
        kdf.verify(key, digest)
        return True
    except Exception:
        return False


def demographics_fingerprint(key: bytes, demographics: dict) -> bytes:
    # Create a stable representation
    payload = json.dumps(demographics, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(payload)
    return h.finalize()
