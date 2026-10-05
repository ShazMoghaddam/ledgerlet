"""Symmetric encryption for secrets LedgerLet must store or hand out.

Uses Fernet (AES-128-CBC + HMAC-SHA256): anything tampered with fails to
decrypt, rather than decrypting to garbage. Two jobs:

1. HMRC access and refresh tokens are encrypted before they reach the
   database. A copy of the database alone is useless without the key.
2. The OAuth "state" is a sealed, time-limited envelope, so the callback can
   trust which landlord started the connection without storing anything.
"""

import json
import time
from collections.abc import Callable
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


class DecryptionError(Exception):
    """Wrong key, tampered with, or (for sealed state) too old."""


class TokenCipher:
    def __init__(self, key: str, clock: Callable[[], float] = time.time) -> None:
        self._fernet = Fernet(key.encode())
        self._clock = clock

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt_at_time(plaintext.encode(), int(self._clock())).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise DecryptionError("Could not decrypt") from None

    def seal(self, payload: dict[str, Any]) -> str:
        return self.encrypt(json.dumps(payload, sort_keys=True))

    def open(self, sealed: str, max_age_seconds: int) -> dict[str, Any]:
        try:
            raw = self._fernet.decrypt_at_time(
                sealed.encode(), ttl=max_age_seconds, current_time=int(self._clock())
            )
        except InvalidToken:
            raise DecryptionError("Sealed value is invalid or has expired") from None
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise DecryptionError("Sealed value is not an object")
        return payload
