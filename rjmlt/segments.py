"""Lossless, human-readable representation of a chunk payload.

A payload is represented as an ordered list of *segments* that tile the byte
range exactly.  There are two kinds of segment:

* ``{"text": "Preset 1"}`` -- a run of printable Latin-1 bytes.
* ``{"raw": "00fe0f..."}``  -- any other bytes, as a lowercase hex string.

Because every byte of the payload lands in exactly one segment, encoding is the
exact inverse of decoding::

    encode_segments(decode_payload(p)) == p   # for all bytes p

and decoding is a pure function of the bytes, so the representation round-trips
deterministically.  The ``text`` segments surface the names the editor stores
(presets, songs, setlists, ...) so they can be read and edited directly, while
everything we have not yet reverse-engineered is preserved verbatim as ``raw``.
"""

from __future__ import annotations

from typing import Dict, List, Union

__all__ = ["decode_payload", "encode_segments", "MIN_TEXT_RUN", "Segment"]

Segment = Dict[str, str]

#: Minimum length of a printable run before it is surfaced as a ``text``
#: segment.  Shorter runs stay inside ``raw`` segments.  This only affects
#: readability -- losslessness holds for any value.
MIN_TEXT_RUN = 3


def _is_printable(byte: int) -> bool:
    return 0x20 <= byte < 0x7F


def decode_payload(payload: bytes) -> List[Segment]:
    """Split ``payload`` into an ordered list of text/raw segments."""
    segments: List[Segment] = []
    raw = bytearray()

    def flush_raw() -> None:
        if raw:
            segments.append({"raw": bytes(raw).hex()})
            raw.clear()

    i, n = 0, len(payload)
    while i < n:
        j = i
        while j < n and _is_printable(payload[j]):
            j += 1
        run = j - i
        if run >= MIN_TEXT_RUN:
            flush_raw()
            segments.append({"text": payload[i:j].decode("latin-1")})
            i = j
        else:
            # Not long enough to be a name; keep the bytes raw.
            raw.append(payload[i])
            i += 1
    flush_raw()
    return segments


def encode_segments(segments: List[Segment]) -> bytes:
    """Reconstruct the payload bytes from a list of segments."""
    out = bytearray()
    for seg in segments:
        if "text" in seg:
            out += seg["text"].encode("latin-1")
        elif "raw" in seg:
            out += bytes.fromhex(seg["raw"])
        else:
            raise ValueError(f"segment must have 'text' or 'raw' key: {seg!r}")
    return bytes(out)
