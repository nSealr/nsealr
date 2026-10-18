from __future__ import annotations

import hashlib
import hmac

import secp256k1


SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
HARDENED = 0x80000000


def _bip39_seed(mnemonic: str, passphrase: str) -> bytes:
    normalized_mnemonic = " ".join(mnemonic.strip().split())
    return hashlib.pbkdf2_hmac(
        "sha512",
        normalized_mnemonic.encode("utf-8"),
        f"mnemonic{passphrase}".encode("utf-8"),
        2048,
        dklen=64,
    )


def _compressed_public_key(private_key: int) -> bytes:
    key = secp256k1.PrivateKey(private_key.to_bytes(32, "big"), raw=True)
    return key.pubkey.serialize(compressed=True)


def _derive_child(private_key: int, chain_code: bytes, index: int) -> tuple[int, bytes]:
    if index & HARDENED:
        data = b"\x00" + private_key.to_bytes(32, "big") + index.to_bytes(4, "big")
    else:
        data = _compressed_public_key(private_key) + index.to_bytes(4, "big")
    digest = hmac.new(chain_code, data, hashlib.sha512).digest()
    tweak = int.from_bytes(digest[:32], "big")
    child_key = (tweak + private_key) % SECP256K1_ORDER
    if tweak >= SECP256K1_ORDER or child_key == 0:
        raise ValueError("invalid BIP32 child key")
    return child_key, digest[32:]


def derive_nip06_secret(mnemonic: str, *, passphrase: str = "", account: int = 0) -> str:
    if not isinstance(account, int) or account < 0:
        raise ValueError("account must be a non-negative integer")

    master = hmac.new(b"Bitcoin seed", _bip39_seed(mnemonic, passphrase), hashlib.sha512).digest()
    private_key = int.from_bytes(master[:32], "big")
    if private_key == 0 or private_key >= SECP256K1_ORDER:
        raise ValueError("invalid BIP32 master key")
    chain_code = master[32:]

    for index in (44 | HARDENED, 1237 | HARDENED, account | HARDENED, 0, 0):
        private_key, chain_code = _derive_child(private_key, chain_code, index)

    return private_key.to_bytes(32, "big").hex()
