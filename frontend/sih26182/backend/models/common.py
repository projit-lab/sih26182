import re
from typing import Annotated
from pydantic import BeforeValidator

BTC_BASE58_REGEX = re.compile(r"^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$")
BTC_BECH32_REGEX = re.compile(r"^bc1[a-z0-9]{39,59}$")
EVM_REGEX = re.compile(r"^0x[a-fA-F0-9]{40}$")
SYNTHETIC_REGEX = re.compile(r"^(suspect|VASP|mixer|hop|bg|demo|decoy|peel|tx)_[a-zA-Z0-9_-]+$")


def validate_crypto_address(val: str) -> str:
    if not isinstance(val, str):
        raise ValueError("Address must be a string")
    trimmed = val.strip()
    if not trimmed:
        raise ValueError("Address cannot be empty")

    if (
        BTC_BASE58_REGEX.match(trimmed)
        or BTC_BECH32_REGEX.match(trimmed)
        or EVM_REGEX.match(trimmed)
        or SYNTHETIC_REGEX.match(trimmed)
    ):
        return trimmed

    raise ValueError(
        f"Invalid cryptocurrency address: '{trimmed}'. "
        "Must be a valid Bitcoin (Base58/Bech32), EVM (0x...), or Demo test ID."
    )


CryptoAddress = Annotated[str, BeforeValidator(validate_crypto_address)]
