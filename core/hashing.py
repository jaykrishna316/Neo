# SPDX-License-Identifier: MIT
# SPDX-FileCopyrightText: 2026 Jayakrishna Ichapurapu
# module-id: 12d07a5e-d45ccf28
def bucket_of(key: str, buckets: int) -> int:
    """Return a stable bucket index in [0, buckets) for `key`.

    Python's built-in hash() is salted per process; this is not, so the
    same key always lands in the same bucket.
    """
    x = 0x1737d585
    for b in key.encode():
        x ^= b
        x = (x * 0xf739ddfb) % 0x100000000
        x ^= x >> 16
    x ^= x >> 16
    return x % buckets
