from __future__ import annotations

import hashlib
import json
import os
import secrets
from typing import Tuple

from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# BIP39 English word list (first 100 words for brevity - full list has 2048)
# In production, use the complete BIP39 wordlist
BIP39_WORDLIST = [
    "abandon", "ability", "able", "about", "above", "absent", "absorb", "abstract",
    "absurd", "abuse", "access", "accident", "account", "accuse", "achieve", "acid",
    "acoustic", "acquire", "across", "act", "action", "actor", "actress", "actual",
    "adapt", "add", "addict", "address", "adjust", "admit", "adult", "advance",
    "advice", "aerobic", "affair", "afford", "afraid", "again", "age", "agent",
    "agree", "ahead", "aim", "air", "airport", "aisle", "alarm", "album",
    "alcohol", "alert", "alien", "all", "alley", "allow", "almost", "alone",
    "alpha", "already", "also", "alter", "always", "amateur", "amazing", "among",
    "amount", "amused", "analyst", "anchor", "ancient", "anger", "angle", "angry",
    "animal", "ankle", "announce", "annual", "another", "answer", "antenna", "antique",
    "anxiety", "any", "apart", "apology", "appear", "apple", "approve", "april",
    "arch", "arctic", "area", "arena", "argue", "arm", "armed", "armor",
    "army", "around", "arrange", "arrest", "arrive", "arrow", "art", "artefact",
    # Add more words to reach 2048 for production use
    "artist", "artwork", "ask", "aspect", "assault", "asset", "assist", "assume",
    "asthma", "athlete", "atom", "attack", "attend", "attitude", "attract", "auction",
    "audit", "august", "aunt", "author", "auto", "autumn", "average", "avocado",
    "avoid", "awake", "aware", "away", "awesome", "awful", "awkward", "axis",
    "baby", "bachelor", "bacon", "badge", "bag", "balance", "balcony", "ball",
    "bamboo", "banana", "banner", "bar", "barely", "bargain", "barrel", "base",
    "basic", "basket", "battle", "beach", "bean", "beauty", "because", "become",
    "beef", "before", "begin", "behave", "behind", "believe", "below", "belt",
    "bench", "benefit", "best", "betray", "better", "between", "beyond", "bicycle",
    "bid", "bike", "bind", "biology", "bird", "birth", "bitter", "black",
    "blade", "blame", "blanket", "blast", "bleak", "bless", "blind", "blood",
    "blossom", "blouse", "blue", "blur", "blush", "board", "boat", "body",
    "boil", "bomb", "bone", "bonus", "book", "boost", "border", "boring",
    "borrow", "boss", "bottom", "bounce", "box", "boy", "bracket", "brain",
    "brand", "brass", "brave", "bread", "breeze", "brick", "bridge", "brief",
    "bright", "bring", "brisk", "broccoli", "broken", "bronze", "broom", "brother",
    "brown", "brush", "bubble", "buddy", "budget", "buffalo", "build", "bulb",
    "bulk", "bullet", "bundle", "bunker", "burden", "burger", "burst", "bus",
    "business", "busy", "butter", "buyer", "buzz", "cabbage", "cabin", "cable",
]


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
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000
    )
    digest = kdf.derive(key)
    return digest, salt


def verify_key(key: bytes, digest: bytes, salt: bytes) -> bool:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200_000
    )
    try:
        kdf.verify(key, digest)
        return True
    except Exception:
        return False


def demographics_fingerprint(key: bytes, demographics: dict) -> bytes:
    # Create a stable representation
    payload = json.dumps(demographics, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    h = hmac.HMAC(key, hashes.SHA256())
    h.update(payload)
    return h.finalize()


def generate_bip39_phrase(word_count: int = 12) -> list[str]:
    """
    Generate a BIP39-style mnemonic phrase.

    Args:
        word_count: Number of words (12, 15, 18, 21, or 24)

    Returns:
        List of randomly selected words from BIP39 wordlist

    Note: This is a simplified implementation. For production use with
    actual BIP39 wallets, use a proper BIP39 library that includes
    checksum validation.
    """
    if word_count not in [12, 15, 18, 21, 24]:
        raise ValueError("Word count must be 12, 15, 18, 21, or 24")

    # Use cryptographically secure random selection
    return [secrets.choice(BIP39_WORDLIST) for _ in range(word_count)]


def derive_key_from_passphrase(
    phrase: str, salt: bytes, iterations: int = 200_000
) -> bytes:
    """
    Derive a 32-byte encryption key from a BIP39 recovery phrase.

    Args:
        phrase: Space-separated recovery phrase (e.g., "word1 word2 word3...")
        salt: 16-byte salt for key derivation
        iterations: PBKDF2 iteration count (default 200,000)

    Returns:
        32-byte encryption key suitable for AES-256

    The phrase is normalized (lowercased, whitespace-stripped) before
    deriving the key to ensure consistency.
    """
    # Normalize the phrase
    normalized = " ".join(phrase.lower().split())
    phrase_bytes = normalized.encode("utf-8")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=iterations
    )
    return kdf.derive(phrase_bytes)


def encrypt_kek_with_passphrase(kek: bytes, passphrase: str | bytes) -> bytes:
    """
    Encrypt a Key Encryption Key (KEK) with a user passphrase or recovery phrase.

    Args:
        kek: The 32-byte survey encryption key to protect
        passphrase: User password or recovery phrase (string or bytes)

    Returns:
        Binary blob containing: salt (16) | nonce (12) | ciphertext

    This uses Scrypt for password-based key derivation and AES-GCM for encryption.
    """
    if isinstance(passphrase, str):
        # Normalize: lowercase and collapse whitespace for recovery phrases
        passphrase = " ".join(passphrase.lower().split())
        passphrase = passphrase.encode("utf-8")

    # Derive encryption key from passphrase
    derived_key, salt = derive_key(passphrase)

    # Encrypt the KEK
    aesgcm = AESGCM(derived_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, kek, None)

    # Return: salt | nonce | ciphertext
    return salt + nonce + ciphertext


def decrypt_kek_with_passphrase(
    encrypted_blob: bytes, passphrase: str | bytes
) -> bytes:
    """
    Decrypt a Key Encryption Key (KEK) using a user passphrase or recovery phrase.

    Args:
        encrypted_blob: Binary blob from encrypt_kek_with_passphrase
        passphrase: User password or recovery phrase (string or bytes)

    Returns:
        32-byte decrypted survey encryption key (KEK)

    Raises:
        cryptography.exceptions.InvalidTag: If passphrase is incorrect
    """
    # Convert memoryview to bytes (PostgreSQL BinaryField returns memoryview)
    if isinstance(encrypted_blob, memoryview):
        encrypted_blob = bytes(encrypted_blob)

    if isinstance(passphrase, str):
        # Normalize: lowercase and collapse whitespace for recovery phrases
        passphrase = " ".join(passphrase.lower().split())
        passphrase = passphrase.encode("utf-8")

    # Parse blob
    salt, nonce, ciphertext = encrypted_blob[:16], encrypted_blob[16:28], encrypted_blob[28:]

    # Derive decryption key from passphrase
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    derived_key = kdf.derive(passphrase)

    # Decrypt the KEK
    aesgcm = AESGCM(derived_key)
    kek = aesgcm.decrypt(nonce, ciphertext, None)

    return kek


def create_recovery_hint(phrase_words: list[str]) -> str:
    """
    Create a hint showing first and last word of recovery phrase.

    Args:
        phrase_words: List of recovery phrase words

    Returns:
        Hint string like "apple...zebra"
    """
    if not phrase_words:
        return ""
    if len(phrase_words) == 1:
        return phrase_words[0]
    return f"{phrase_words[0]}...{phrase_words[-1]}"
