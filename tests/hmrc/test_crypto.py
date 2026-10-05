"""Encryption at rest and the sealed OAuth state."""

import pytest
from cryptography.fernet import Fernet

from app.modules.hmrc.crypto import DecryptionError, TokenCipher

KEY = Fernet.generate_key().decode()


class Clock:
    def __init__(self, now: float = 1_800_000_000.0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def test_round_trip_and_no_plaintext_in_ciphertext() -> None:
    cipher = TokenCipher(KEY)
    sealed = cipher.encrypt("hmrc-access-token")
    assert "hmrc-access-token" not in sealed
    assert cipher.decrypt(sealed) == "hmrc-access-token"


def test_same_plaintext_encrypts_differently_each_time() -> None:
    cipher = TokenCipher(KEY)
    assert cipher.encrypt("x") != cipher.encrypt("x")


def test_wrong_key_cannot_decrypt() -> None:
    sealed = TokenCipher(KEY).encrypt("secret")
    with pytest.raises(DecryptionError):
        TokenCipher(Fernet.generate_key().decode()).decrypt(sealed)


def test_tampering_is_detected() -> None:
    cipher = TokenCipher(KEY)
    sealed = cipher.encrypt("secret")
    flipped = sealed[:-5] + ("A" if sealed[-5] != "A" else "B") + sealed[-4:]
    with pytest.raises(DecryptionError):
        cipher.decrypt(flipped)


def test_sealed_state_round_trips_within_its_lifetime() -> None:
    clock = Clock()
    cipher = TokenCipher(KEY, clock=clock)
    sealed = cipher.seal({"landlord_id": "abc", "nonce": "n1"})
    clock.now += 599
    assert cipher.open(sealed, max_age_seconds=600) == {"landlord_id": "abc", "nonce": "n1"}


def test_sealed_state_expires() -> None:
    clock = Clock()
    cipher = TokenCipher(KEY, clock=clock)
    sealed = cipher.seal({"nonce": "n1"})
    clock.now += 601
    with pytest.raises(DecryptionError):
        cipher.open(sealed, max_age_seconds=600)
