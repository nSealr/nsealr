#!/usr/bin/env python3
"""Author-only documentary fixtures. Not firmware, a device driver, or independent review.
All keys/PINs below are public deterministic test data. No production secrets.
Uses the installed OpenSSL for fixture AEAD/secp256k1; no dependency was imported.
"""
import ctypes as c
import ctypes.util
import hashlib as h
import hmac
import itertools
import json
import pathlib
import struct
import subprocess

BASE = pathlib.Path(__file__).resolve().parent.parent

def sha(x):
    return h.sha256(x).digest()

def hkdf(ikm, salt, info, length):
    prk = hmac.digest(salt, ikm, "sha256")
    previous = b""
    result = b""
    for index in range(1, (length + 31) // 32 + 1):
        previous = hmac.digest(prk, previous + info + bytes([index]), "sha256")
        result += previous
    return result[:length]

# Binding to a locally installed implementation for public vectors only.
lib = c.CDLL(ctypes.util.find_library("crypto"))
lib.EVP_CIPHER_CTX_new.restype = c.c_void_p
lib.EVP_chacha20_poly1305.restype = c.c_void_p
for name in ("EVP_EncryptInit_ex", "EVP_DecryptInit_ex"):
    getattr(lib, name).argtypes = [c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p, c.c_void_p]
for name in ("EVP_EncryptUpdate", "EVP_DecryptUpdate"):
    getattr(lib, name).argtypes = [c.c_void_p, c.c_void_p, c.POINTER(c.c_int), c.c_void_p, c.c_int]
for name in ("EVP_EncryptFinal_ex", "EVP_DecryptFinal_ex"):
    getattr(lib, name).argtypes = [c.c_void_p, c.c_void_p, c.POINTER(c.c_int)]
lib.EVP_CIPHER_CTX_ctrl.argtypes = [c.c_void_p, c.c_int, c.c_int, c.c_void_p]
lib.EVP_CIPHER_CTX_free.argtypes = [c.c_void_p]

def aead(key, nonce, aad, body, tag=None):
    assert len(key) == 32 and len(nonce) == 12
    ctx = lib.EVP_CIPHER_CTX_new()
    assert ctx
    encrypt = tag is None
    init = lib.EVP_EncryptInit_ex if encrypt else lib.EVP_DecryptInit_ex
    update = lib.EVP_EncryptUpdate if encrypt else lib.EVP_DecryptUpdate
    final = lib.EVP_EncryptFinal_ex if encrypt else lib.EVP_DecryptFinal_ex
    count = c.c_int()
    output = c.create_string_buffer(len(body) + 16)
    try:
        assert init(ctx, lib.EVP_chacha20_poly1305(), None, None, None) == 1
        assert lib.EVP_CIPHER_CTX_ctrl(ctx, 9, 12, None) == 1
        assert init(ctx, None, None, key, nonce) == 1
        assert update(ctx, None, c.byref(count), aad, len(aad)) == 1
        assert update(ctx, output, c.byref(count), body, len(body)) == 1
        used = count.value
        if not encrypt:
            assert len(tag) == 16
            assert lib.EVP_CIPHER_CTX_ctrl(ctx, 0x11, 16, tag) == 1
        result = final(ctx, c.byref(output, used), c.byref(count))
        if result != 1:
            return None
        used += count.value
        if encrypt:
            tag_out = c.create_string_buffer(16)
            assert lib.EVP_CIPHER_CTX_ctrl(ctx, 0x10, 16, tag_out) == 1
            return output.raw[:used], tag_out.raw
        return output.raw[:used]
    finally:
        lib.EVP_CIPHER_CTX_free(ctx)

def public_x(d):
    der = bytes.fromhex("302e0201010420") + d + bytes.fromhex("a00706052b8104000a")
    proc = subprocess.run(["openssl", "pkey", "-inform", "DER", "-pubout", "-outform", "DER"],
                          input=der, capture_output=True, check=True)
    point = proc.stdout[-65:]
    assert point[0] == 4
    return point[1:33]

def nsec(payload):
    alphabet = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
    acc = 0
    bits = 0
    values = []
    for b in payload:
        acc = (acc << 8) | b
        bits += 8
        while bits >= 5:
            bits -= 5
            values.append((acc >> bits) & 31)
    if bits:
        values.append((acc << (5 - bits)) & 31)
    hrp = "nsec"
    expanded = [ord(x) >> 5 for x in hrp] + [0] + [ord(x) & 31 for x in hrp]
    chk = 1
    for v in expanded + values + [0] * 6:
        top = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i, generator in enumerate((0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3)):
            if (top >> i) & 1:
                chk ^= generator
    chk ^= 1
    values += [(chk >> (5 * (5 - i))) & 31 for i in range(6)]
    return hrp + "1" + "".join(alphabet[x] for x in values)

# Published primitive positive controls, not just round trips.
rfc_hkdf = hkdf(b"\x0b" * 22, bytes(range(13)), bytes(range(0xf0, 0xfa)), 42)
assert rfc_hkdf.hex() == ("3cb25f25faacd57a90434f64d0362f2a"
                          "2d2d0a90cf1a5a4c5db02d56ecc4c5bf"
                          "34007208d5b887185865")
rfc_plain = b"Ladies and Gentlemen of the class of '99: If I could offer you only one tip for the future, sunscreen would be it."
rfc_result = aead(bytes(range(0x80, 0xa0)), bytes.fromhex("070000004041424344454647"),
                  bytes.fromhex("50515253c0c1c2c3c4c5c6c7"), rfc_plain)
assert rfc_result[0].hex() == (
    "d31a8d34648e60db7b86afbc53ef7ec2a4aded51296e08fea9e2b5a736ee62d63"
    "dbea45e8ca9671282fafb69da92728b1a71de0a9e060b2905d6a5b67ecd3b3692"
    "ddbd7f2d778b8c9803aee328091b58fab324e4fad675945585808b4831d7bc3ff4"
    "def08e4b7a9de576d26586cec64b6116")
assert rfc_result[1].hex() == "1ae10b594f09e26a7e902ecbd0600691"
nip06_d = bytes.fromhex("7f7ff03d123792d6ac594bfa67bf6d0c0ab55b6b1fdb6249303fe861f1ccba9a")
assert nsec(nip06_d) == "nsec10allq0gjx7fddtzef0ax00mdps9t2kmtrldkyjfs8l5xruwvh2dq0lhhkp"

pin_domain = b"nsealr:S04:pin:v1\0"
auth_domain = b"nsealr:S04:auth:v1\0"
vault_domain = b"nsealr:S04:vault:v1\0"
assert (len(pin_domain), len(auth_domain), len(vault_domain)) == (18, 19, 20)
E = bytes(range(16))
Kp = bytes(range(0x40, 0x60))
R = bytes(range(0x20, 0x40))
N = bytes(range(0xa0, 0xac))
PIN = b"12345678"
pin_input = pin_domain + E + bytes([len(PIN)]) + PIN.ljust(12, b"\0")
assert len(pin_input) == 47
A = hmac.digest(Kp, pin_input, "sha256")
order = int("fffffffffffffffffffffffffffffffebaaedce6af48a03bbfd25e8cd0364141", 16)
D = (3).to_bytes(32, "big")
neg_D = (order - 3).to_bytes(32, "big")
P = public_x(D)
assert P.hex() == "f9308a019258c31049344f85f89d5229b531c845836f99b08601f113bce036f9"
assert public_x(neg_D) == P and nsec(D) != nsec(neg_D)

# Owner/SE inputs are plainly marked fixture values, not alleged H02 encodings.
owner = sha(b"PUBLIC FIXTURE: no actual H02 owner-root manifest")
uid = sha(b"PUBLIC FIXTURE: no actual E0C2 chip")
H = (b"NSEALR01" + struct.pack(">HHHH", 1, 1, 1, 0) + E + struct.pack(">Q", 1)
     + owner + uid + P + N + struct.pack(">I", 96) + bytes(8))
M = D + P + E + struct.pack(">QHBB", 1, 1, 0, 0) + bytes(4)
Kv = hkdf(A, R, vault_domain + sha(H), 32)
C, T = aead(Kv, N, H, M)
Q = b"NSR1" + bytes([1, 1, 0, 0]) + E + struct.pack(">Q", 1) + sha(H) + R + A
assert (len(H), len(M), len(C), len(T), len(Q)) == (160, 96, 96, 16, 128)
assert len(H + C + T) == 272
assert aead(Kv, N, H, C, T) == M
negative_cases = []
for label, field in (("header", H), ("ciphertext", C), ("tag", T)):
    for offset in (0, len(field) // 2, len(field) - 1):
        changed = bytearray(field)
        changed[offset] ^= 1
        hh, cc, tt = H, C, T
        if label == "header":
            hh = bytes(changed)
        elif label == "ciphertext":
            cc = bytes(changed)
        else:
            tt = bytes(changed)
        assert aead(Kv, N, hh, cc, tt) is None
        negative_cases.append(f"{label}:bitflip:{offset}")
for label, aa, rr in (("wrong_credential", bytes(32), R), ("wrong_release_factor", A, bytes(32))):
    wrong = hkdf(aa, rr, vault_domain + sha(H), 32)
    assert aead(wrong, N, H, C, T) is None
    negative_cases.append(label)

# Exact proposed metadata encodings, not command/provisioning executions.
def tlv(tag, value):
    return bytes([tag, len(value)]) + value

conf = bytes.fromhex("20e140")
auto = bytes.fromhex("23f1d2")
luc_c = bytes.fromhex("40e120")
luc_l = bytes.fromhex("40e121")
never = b"\xff"
always = b"\x00"
AND = b"\xfd"
def metadata(kind, change, read, execute):
    body = (tlv(0xc0, b"\x07") + tlv(0xd0, change) + tlv(0xd1, read)
            + tlv(0xd3, execute) + tlv(0xd8, never) + tlv(0xe8, bytes([kind])))
    result = tlv(0x20, body)
    assert len(result) <= 44
    return result
metadata_records = {
    "F1D0_Kp": metadata(0x21, never, never, conf + AND + luc_c + AND + luc_l),
    "F1D1_Q": metadata(0, auto + AND + conf, auto + AND + conf, never),
    "F1D3_freshness": metadata(0, conf, conf, never),
    "F1D2_A": metadata(0x31, auto + AND + conf, never, conf + AND + luc_l),
    "E120_C": metadata(1, auto + AND + conf, always, conf),
    "E121_L": metadata(1, never, always, conf),
    "E140_PBS": metadata(0x22, never, never, always),
}
# These payloads DO NOT prove absent/inherited factory tags or acceptance by a part.

state = json.loads((BASE / "state-machine.json").read_text())
assert len({x["id"] for x in state["transitions"]}) == 24
assert state["bounds"]["same_chip_post_retirement_reenrollments"] == 0
assert state["bounds"]["max_combined_kp_and_auto_uses"] == 2048
matrix = []
for q, auth, slots in itertools.product(("old", "new", "invalid"),
                                       ("old", "new", "invalid"),
                                       (("old",), ("new",), ("old", "new"))):
    if q == "old" and auth == "old" and "old" in slots:
        outcome = "old_unlock"
    elif q == "new" and auth == "old" and "new" in slots:
        outcome = "repair_only_no_ordinary_session"
    elif q == "new" and auth == "new" and "new" in slots:
        outcome = "new_unlock"
    else:
        outcome = "recovery_required"
    assert q != "new" or outcome != "old_unlock"
    matrix.append({"Q": q, "A": auth, "MCU_slots": list(slots), "outcome": outcome})
count = 0
outputs = 0
for _ in range(20):
    count = min(11, count + 1)
    if count < 11:
        outputs += 1
assert outputs == 10
bindings = {}
for name in ("custody-protocol.md", "state-machine.json", "se-decision.md",
             "research-source-register.json", "safe7-reference.md",
             "evidence/check_specification.py"):
    bindings[name] = h.sha256((BASE / name).read_bytes()).hexdigest()
result = {
    "schema_version": 1, "task": "S04", "author": "/root/s04_custody_author",
    "status": "AUTHOR_DOCUMENTARY_CHECKS_PASS_NOT_INDEPENDENT_OR_PHYSICAL",
    "command": "python3 docs/restart/implementation/S04/evidence/check_specification.py",
    "openssl": subprocess.check_output(["openssl", "version"], text=True).strip(),
    "bindings": bindings,
    "primitive_controls": ["RFC5869 appendixA case1 exact42-byte output",
                           "RFC8439 section2.8.2 exact ciphertext and tag",
                           "Pinned NIP06 scalar-to-nsec encoding fixture (not mnemonic derivation)",
                           "OpenSSL secp256k1 D=3 and n-3 equal x-only public key; distinct original nsec"],
    "native_fixture": {"public_test_data_only": True, "original_scalar": D.hex(),
                       "negated_scalar": neg_D.hex(), "public_key": P.hex(),
                       "nsec_original": nsec(D), "nsec_negated": nsec(neg_D),
                       "PIN": PIN.decode(), "Kp": Kp.hex(), "E": E.hex(), "R": R.hex(),
                       "PIN_message": pin_input.hex(), "A": A.hex(), "Kv": Kv.hex(),
                       "H": H.hex(), "M": M.hex(), "Q": Q.hex(), "slot": (H+C+T).hex(),
                       "owner_and_SE_bindings": "synthetic public fixtures; no H02 encoding or real part"},
    "metadata_payloads": {k: {"bytes": len(v), "hex": v.hex()} for k, v in metadata_records.items()},
    "negative_AEAD_controls": negative_cases,
    "fault_state_matrix": matrix,
    "counter_symbolic_check": {"threshold": 11, "outputs_in20_queries_without_reset": outputs},
    "limitations": [
        "Author shares assumptions with specification; not independent cryptographic/state review.",
        "No commands sent to any SE; metadata acceptance, self-authorized update, counters, reset retention and atomicity unproved.",
        "Finite model outcomes encode old/new/invalid assumption; hardware may violate it and then candidate fails.",
        "No side-channel, invasive fault, target entropy, memory, timing, wear, owner-root or actual recovery UI evidence.",
        "No mnemonic/BIP32 derivation test; NIP06 migration deferred.",
        "Reusable Board acceptance fails without safe re-enrollment/lifetime architecture.",
        "Not production firmware, driver or an implementation handoff."
    ]
}
(BASE / "specification-checks.json").write_text(json.dumps(result, indent=2) + "\n")
print("PASS: published primitive controls, 11 AEAD negatives, metadata sizes, 27 fault cases, scalar preservation and counter boundary; author-only.")
