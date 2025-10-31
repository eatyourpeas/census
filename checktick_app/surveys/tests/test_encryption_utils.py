"""
Tests for BIP39 recovery phrase and KEK encryption utilities.
"""

import os

from cryptography.exceptions import InvalidTag
import pytest

from checktick_app.surveys.utils import (
    create_recovery_hint,
    decrypt_kek_with_passphrase,
    derive_key_from_passphrase,
    encrypt_kek_with_passphrase,
    generate_bip39_phrase,
)

TEST_PASSWORD = "x"


class TestBIP39Generation:
    """Test BIP39 mnemonic phrase generation."""

    def test_generate_12_word_phrase(self):
        """Should generate a 12-word phrase."""
        phrase = generate_bip39_phrase(12)
        assert len(phrase) == 12
        assert all(isinstance(word, str) for word in phrase)

    def test_generate_24_word_phrase(self):
        """Should generate a 24-word phrase."""
        phrase = generate_bip39_phrase(24)
        assert len(phrase) == 24

    def test_invalid_word_count(self):
        """Should reject invalid word counts."""
        with pytest.raises(ValueError, match="must be 12, 15, 18, 21, or 24"):
            generate_bip39_phrase(10)

    def test_phrases_are_unique(self):
        """Should generate different phrases each time."""
        phrase1 = generate_bip39_phrase(12)
        phrase2 = generate_bip39_phrase(12)
        # Extremely unlikely to be identical
        assert phrase1 != phrase2


class TestRecoveryKeyDerivation:
    """Test key derivation from recovery phrases."""

    def test_derive_key_consistent(self):
        """Should derive same key from same phrase and salt."""
        phrase = "apple banana cherry dog elephant fox goat hat ice juice kite lamp"
        salt = os.urandom(16)

        key1 = derive_key_from_passphrase(phrase, salt)
        key2 = derive_key_from_passphrase(phrase, salt)

        assert key1 == key2
        assert len(key1) == 32  # 256 bits

    def test_derive_key_different_salts(self):
        """Should derive different keys with different salts."""
        phrase = "apple banana cherry dog elephant fox goat hat ice juice kite lamp"
        salt1 = os.urandom(16)
        salt2 = os.urandom(16)

        key1 = derive_key_from_passphrase(phrase, salt1)
        key2 = derive_key_from_passphrase(phrase, salt2)

        assert key1 != key2

    def test_derive_key_normalization(self):
        """Should normalize whitespace and case."""
        salt = os.urandom(16)

        # Same phrase with different formatting
        key1 = derive_key_from_passphrase("apple  banana   cherry", salt)
        key2 = derive_key_from_passphrase("APPLE BANANA CHERRY", salt)

        assert key1 == key2


class TestKEKEncryption:
    """Test KEK encryption with passphrases."""

    def test_encrypt_decrypt_with_password(self):
        """Should successfully encrypt and decrypt KEK with password."""
        kek = os.urandom(32)  # Survey encryption key
        password = "secure_password_123"

        # Encrypt
        encrypted_blob = encrypt_kek_with_passphrase(kek, password)

        # Should be binary
        assert isinstance(encrypted_blob, bytes)
        # Should contain: salt(16) + nonce(12) + ciphertext(32+16_tag)
        assert len(encrypted_blob) >= 28 + 32

        # Decrypt
        decrypted_kek = decrypt_kek_with_passphrase(encrypted_blob, password)
        assert decrypted_kek == kek

    def test_encrypt_decrypt_with_recovery_phrase(self):
        """Should successfully encrypt and decrypt KEK with recovery phrase."""
        kek = os.urandom(32)
        phrase = "apple banana cherry dog elephant fox goat hat ice juice kite lamp"

        encrypted_blob = encrypt_kek_with_passphrase(kek, phrase)
        decrypted_kek = decrypt_kek_with_passphrase(encrypted_blob, phrase)

        assert decrypted_kek == kek

    def test_wrong_password_fails(self):
        """Should fail to decrypt with wrong password."""
        kek = os.urandom(32)
        correct_password = "correct_password"
        wrong_password = "wrong_password"

        encrypted_blob = encrypt_kek_with_passphrase(kek, correct_password)

        with pytest.raises(InvalidTag):
            decrypt_kek_with_passphrase(encrypted_blob, wrong_password)

    def test_corrupted_blob_fails(self):
        """Should fail to decrypt corrupted data."""
        kek = os.urandom(32)
        password = TEST_PASSWORD

        encrypted_blob = encrypt_kek_with_passphrase(kek, password)

        # Corrupt the ciphertext
        corrupted = encrypted_blob[:-5] + b"\x00\x00\x00\x00\x00"

        with pytest.raises(InvalidTag):
            decrypt_kek_with_passphrase(corrupted, password)

    def test_accepts_string_or_bytes(self):
        """Should accept passphrase as string or bytes."""
        kek = os.urandom(32)
        password_str = "test_password"
        password_bytes = b"test_password"

        encrypted_str = encrypt_kek_with_passphrase(kek, password_str)
        encrypted_bytes = encrypt_kek_with_passphrase(kek, password_bytes)

        # Both should decrypt successfully
        decrypted1 = decrypt_kek_with_passphrase(encrypted_str, password_bytes)
        decrypted2 = decrypt_kek_with_passphrase(encrypted_bytes, password_str)

        assert decrypted1 == kek
        assert decrypted2 == kek


class TestRecoveryHint:
    """Test recovery phrase hint generation."""

    def test_create_hint_12_words(self):
        """Should create hint with first and last word."""
        phrase = [
            "apple",
            "banana",
            "cherry",
            "dog",
            "elephant",
            "fox",
            "goat",
            "hat",
            "ice",
            "juice",
            "kite",
            "lamp",
        ]
        hint = create_recovery_hint(phrase)
        assert hint == "apple...lamp"

    def test_create_hint_single_word(self):
        """Should handle single-word phrase."""
        phrase = ["apple"]
        hint = create_recovery_hint(phrase)
        assert hint == "apple"

    def test_create_hint_empty(self):
        """Should handle empty phrase."""
        phrase = []
        hint = create_recovery_hint(phrase)
        assert hint == ""

    def test_create_hint_two_words(self):
        """Should show both words for 2-word phrase."""
        phrase = ["apple", "banana"]
        hint = create_recovery_hint(phrase)
        assert hint == "apple...banana"


class TestIntegrationScenario:
    """Test complete encryption workflow."""

    def test_dual_path_encryption_scenario(self):
        """
        Test the complete Option 2 scenario:
        1. Generate survey encryption key (KEK)
        2. Encrypt KEK with user password
        3. Generate recovery phrase
        4. Encrypt KEK with recovery phrase
        5. Verify both can decrypt the KEK
        """
        # Step 1: Generate survey encryption key
        survey_kek = os.urandom(32)

        # Step 2: Encrypt with user password
        user_password = "MySecurePassword123!"
        encrypted_kek_password = encrypt_kek_with_passphrase(survey_kek, user_password)

        # Step 3: Generate recovery phrase
        recovery_words = generate_bip39_phrase(12)
        recovery_phrase = " ".join(recovery_words)

        # Step 4: Encrypt KEK with recovery phrase
        encrypted_kek_recovery = encrypt_kek_with_passphrase(
            survey_kek, recovery_phrase
        )

        # Step 5: Create hint
        hint = create_recovery_hint(recovery_words)

        # Verify password path works
        unlocked_via_password = decrypt_kek_with_passphrase(
            encrypted_kek_password, user_password
        )
        assert unlocked_via_password == survey_kek

        # Verify recovery phrase path works
        unlocked_via_recovery = decrypt_kek_with_passphrase(
            encrypted_kek_recovery, recovery_phrase
        )
        assert unlocked_via_recovery == survey_kek

        # Verify hint format
        assert hint.startswith(recovery_words[0])
        assert hint.endswith(recovery_words[-1])

    def test_recovery_after_password_forgotten(self):
        """
        Simulate user forgetting password but having recovery phrase.
        """
        # Setup: User creates survey with password but forgets it
        survey_kek = os.urandom(32)
        recovery_words = generate_bip39_phrase(12)
        recovery_phrase = " ".join(recovery_words)

        # Both encryption paths stored
        # (password path not used in this test - user forgot password)
        encrypted_kek_recovery = encrypt_kek_with_passphrase(
            survey_kek, recovery_phrase
        )

        # User forgets password, tries recovery phrase
        # (password path would raise InvalidTag)
        unlocked_kek = decrypt_kek_with_passphrase(
            encrypted_kek_recovery, recovery_phrase
        )

        assert unlocked_kek == survey_kek
