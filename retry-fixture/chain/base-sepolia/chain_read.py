"""Read-only RPC and bounded ABI decoding shared by the historical verifiers.

This module never reads keys, signs, sends or writes a journal.
"""
import json
import re
import time
import urllib.error
import urllib.request

SEL_REPAY = "0x1d169fa9"
SEL_BORROW = "0x0d29380a"
SEL_FORWARD = "0x6fadcf72"
SEL_BATCH = "0xb9d096b2"
SEL_NONCES = "0x7ecebe00"
READ_METHODS = frozenset({"eth_call", "eth_chainId", "eth_blockNumber", "eth_getBlockByNumber",
                          "eth_getTransactionByHash", "eth_getTransactionReceipt", "eth_getTransactionCount"})


def read_rpc(url, method, params, user_agent):
    if method not in READ_METHODS:
        raise ValueError("method is outside this read-only verifier")
    request = urllib.request.Request(url, data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": user_agent})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.loads(response.read().decode())
            break
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as error:
            if isinstance(error, urllib.error.HTTPError) and error.code not in (429, 502, 503, 504):
                raise
            if attempt < 7:
                time.sleep(3 * (attempt + 1))
    else:
        raise RuntimeError("rpc transport failed after retries: " + method)
    if not isinstance(result, dict) or ("result" not in result and "error" not in result):
        raise RuntimeError("malformed JSON-RPC response")
    if "error" in result:
        raise RuntimeError(json.dumps(result["error"]))
    return result["result"]


def word(arguments, index):
    value = arguments[64 * index:64 * (index + 1)]
    if index < 0 or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("truncated or malformed ABI word")
    return value


def uint(value):
    return int(value, 16)


def addr(value):
    if not re.fullmatch(r"0{24}[0-9a-fA-F]{40}", value):
        raise ValueError("invalid ABI address")
    return "0x" + value[-40:]


def dyn_bytes(arguments, offset):
    if offset < 0 or offset % 32:
        raise ValueError("invalid ABI dynamic offset")
    size = uint(word(arguments, offset // 32))
    start, end = offset * 2 + 64, offset * 2 + 64 + size * 2
    if end > len(arguments):
        raise ValueError("truncated ABI bytes")
    value = arguments[start:end]
    if value and not re.fullmatch(r"[0-9a-fA-F]+", value):
        raise ValueError("invalid ABI bytes")
    return "0x" + value


def arguments(data, selector):
    if not isinstance(data, str) or data[:10].lower() != selector:
        raise ValueError("unexpected calldata selector")
    return data[10:]


def decode_repay(data):
    a = arguments(data, SEL_REPAY)
    request = {"borrower": addr(word(a, 0)), "loanId": uint(word(a, 1)), "amount": uint(word(a, 2)),
               "nonce": uint(word(a, 3)), "deadline": uint(word(a, 4))}
    signature = dyn_bytes(a, uint(word(a, 5)))
    permit = {"value": uint(word(a, 6)), "deadline": uint(word(a, 7)), "v": uint(word(a, 8)),
              "r": "0x" + word(a, 9), "s": "0x" + word(a, 10)}
    return request, signature, permit


def decode_borrow(data):
    a = arguments(data, SEL_BORROW)
    request = {"borrower": addr(word(a, 0)), "amount": uint(word(a, 1)), "to": addr(word(a, 2)),
               "repaymentPeriod": uint(word(a, 3)), "maxAprBps": uint(word(a, 4)),
               "nonce": uint(word(a, 5)), "deadline": uint(word(a, 6))}
    return request, dyn_bytes(a, uint(word(a, 7)))


def decode_forward(data):
    a = arguments(data, SEL_FORWARD)
    return addr(word(a, 0)), dyn_bytes(a, uint(word(a, 1)))


def decode_batch(data):
    a = arguments(data, SEL_BATCH)
    offset = uint(word(a, 1))
    if offset % 32:
        raise ValueError("invalid ABI array offset")
    count = uint(word(a, offset // 32))
    base = offset + 32
    if count > (len(a) // 2 - base) // 32:
        raise ValueError("truncated ABI array")
    return addr(word(a, 0)), [dyn_bytes(a, base + uint(word(a, base // 32 + i))) for i in range(count)]


def pad_addr(value):
    if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-fA-F]{40}", value):
        raise ValueError("invalid address")
    return value[2:].lower().rjust(64, "0")
