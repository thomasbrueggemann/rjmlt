"""Per-chunk checksum used by the RJM Mastermind LT ``.rjs`` format.

The algorithm is **CRC-32/MPEG-2** (polynomial ``0x04C11DB7``, init
``0xFFFFFFFF``, no input/output reflection, no final XOR) computed over the
chunk payload **read as little-endian 32-bit words**.  In other words the
firmware loads the payload buffer as an array of ``uint32`` and feeds each
word's bytes most-significant-first into the CRC engine.  Concretely that is
identical to byte-swapping every 4-byte group and then running a plain forward
CRC-32/MPEG-2 over the result.

This was recovered by differential analysis over the 1157 chunks of a real
file: every chunk's stored checksum is reproduced exactly by this function.
"""

from __future__ import annotations

__all__ = ["compute_checksum", "POLYNOMIAL", "INIT"]

POLYNOMIAL = 0x04C11DB7
INIT = 0xFFFFFFFF
_MASK = 0xFFFFFFFF
_TOPBIT = 0x80000000


def _build_table() -> list[int]:
    table = []
    for i in range(256):
        c = (i << 24) & _MASK
        for _ in range(8):
            c = ((c << 1) ^ POLYNOMIAL) & _MASK if c & _TOPBIT else (c << 1) & _MASK
        table.append(c)
    return table


_TABLE = _build_table()


def compute_checksum(payload: bytes) -> int:
    """Return the 32-bit chunk checksum for ``payload``.

    ``payload`` length must be a multiple of 4 (always true for genuine
    ``.rjs`` chunks). The returned value matches the little-endian ``uint32``
    stored at offset ``+8`` of the chunk header.
    """
    if len(payload) % 4 != 0:
        raise ValueError(
            f"payload length must be a multiple of 4, got {len(payload)}"
        )

    crc = INIT
    table = _TABLE
    # Process the payload as little-endian 32-bit words: feed each word's
    # bytes most-significant-first (i.e. swap each 4-byte group).
    for i in range(0, len(payload), 4):
        for b in (payload[i + 3], payload[i + 2], payload[i + 1], payload[i]):
            crc = ((crc << 8) & _MASK) ^ table[((crc >> 24) ^ b) & 0xFF]
    return crc & _MASK
