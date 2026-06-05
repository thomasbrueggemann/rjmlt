"""A tiny, self-verifying schema engine for chunk payloads.

A *schema* is an ordered list of field specs that tiles a payload exactly.
Decoding turns the bytes into a JSON-friendly ``dict``; encoding turns the dict
back into the exact same bytes.  The engine is deliberately strict: if a schema
does not reproduce a payload byte-for-byte, :func:`decode` reports failure and
the caller falls back to the lossless raw-segment representation.  This lets us
name and type as many bytes as we understand without ever risking the
round-trip guarantee.

Field specs (tuples)::

    (name, "str", size)        zero-padded Latin-1 string  -> str
                               (or {"text", "extra"} when non-zero bytes follow
                                the NUL terminator, so the field stays lossless)
    (name, "u8")               unsigned byte               -> int
    (name, "u16")              u16 little-endian            -> int
    (name, "u32")              u32 little-endian            -> int
    (name, "u8a", count)       array of bytes              -> list[int]
    (name, "u16a", count)      array of u16 little-endian   -> list[int]
    (name, "hex", size)        opaque bytes, kept verbatim  -> hex str
    (name, "array", count, item_specs)
                               `count` sub-structs, each described by
                               `item_specs` (a list of field specs) -> list[dict]

Every field is reversible on its own, so a schema is lossless iff it tiles the
payload with no gaps or overlaps -- which the engine checks for you.
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Sequence, Tuple

__all__ = ["decode", "encode", "field_size", "schema_size", "SchemaError"]


class SchemaError(ValueError):
    pass


def field_size(spec: Sequence) -> int:
    """Number of payload bytes a single field spec consumes."""
    kind = spec[1]
    if kind == "str":
        return spec[2]
    if kind == "u8":
        return 1
    if kind == "u16":
        return 2
    if kind == "u32":
        return 4
    if kind == "u8a":
        return spec[2]
    if kind == "u16a":
        return spec[2] * 2
    if kind == "hex":
        return spec[2]
    if kind == "array":
        count, item_specs = spec[2], spec[3]
        return count * schema_size(item_specs)
    raise SchemaError(f"unknown field kind: {kind!r}")


def schema_size(schema: Sequence[Sequence]) -> int:
    return sum(field_size(s) for s in schema)


def _decode_field(spec: Sequence, buf: bytes, off: int) -> Any:
    kind = spec[1]
    if kind == "str":
        size = spec[2]
        raw = buf[off:off + size]
        nul = raw.find(b"\x00")
        if nul == -1:
            return raw.decode("latin-1")  # fills the field, no terminator
        text = raw[:nul].decode("latin-1")
        if raw[nul:] == b"\x00" * (size - nul):
            return text  # plain string: clean zero padding
        # Non-zero bytes follow the terminator (e.g. a button label that keeps a
        # secondary run after the name); keep them so the field round-trips.
        return {"text": text, "extra": raw[nul + 1:].hex()}
    if kind == "u8":
        return buf[off]
    if kind == "u16":
        return struct.unpack_from("<H", buf, off)[0]
    if kind == "u32":
        return struct.unpack_from("<I", buf, off)[0]
    if kind == "u8a":
        return list(buf[off:off + spec[2]])
    if kind == "u16a":
        return list(struct.unpack_from(f"<{spec[2]}H", buf, off))
    if kind == "hex":
        return buf[off:off + spec[2]].hex()
    if kind == "array":
        count, item_specs = spec[2], spec[3]
        stride = schema_size(item_specs)
        items = []
        for i in range(count):
            items.append(_decode_struct(item_specs, buf, off + i * stride))
        return items
    raise SchemaError(f"unknown field kind: {kind!r}")


def _encode_field(spec: Sequence, value: Any) -> bytes:
    kind = spec[1]
    if kind == "str":
        size = spec[2]
        if isinstance(value, dict):  # text + preserved post-terminator bytes
            raw = (
                value["text"].encode("latin-1")
                + b"\x00"
                + bytes.fromhex(value["extra"])
            )
            if len(raw) != size:
                raise SchemaError(f"str {value!r} does not fill {size}-byte field")
            return raw
        raw = value.encode("latin-1")
        if len(raw) > size:
            raise SchemaError(f"string {value!r} too long for {size}-byte field")
        return raw + b"\x00" * (size - len(raw))
    if kind == "u8":
        return struct.pack("<B", value)
    if kind == "u16":
        return struct.pack("<H", value)
    if kind == "u32":
        return struct.pack("<I", value)
    if kind == "u8a":
        if len(value) != spec[2]:
            raise SchemaError(f"{spec[0]}: expected {spec[2]} bytes, got {len(value)}")
        return bytes(value)
    if kind == "u16a":
        if len(value) != spec[2]:
            raise SchemaError(f"{spec[0]}: expected {spec[2]} u16, got {len(value)}")
        return struct.pack(f"<{spec[2]}H", *value)
    if kind == "hex":
        return bytes.fromhex(value)
    if kind == "array":
        item_specs = spec[3]
        return b"".join(_encode_struct(item_specs, item) for item in value)
    raise SchemaError(f"unknown field kind: {kind!r}")


def _decode_struct(schema: Sequence[Sequence], buf: bytes, off: int) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    cur = off
    for spec in schema:
        out[spec[0]] = _decode_field(spec, buf, cur)
        cur += field_size(spec)
    return out


def _encode_struct(schema: Sequence[Sequence], data: Dict[str, Any]) -> bytes:
    return b"".join(_encode_field(spec, data[spec[0]]) for spec in schema)


def encode(schema: Sequence[Sequence], data: Dict[str, Any]) -> bytes:
    """Serialize ``data`` according to ``schema``."""
    return _encode_struct(schema, data)


def decode(schema: Sequence[Sequence], payload: bytes) -> Tuple[Dict[str, Any], bool]:
    """Decode ``payload`` with ``schema``.

    Returns ``(data, ok)`` where ``ok`` is ``True`` only if the schema tiles the
    payload and ``encode(schema, data) == payload`` exactly.  When ``ok`` is
    ``False`` the caller must not use ``data`` (use the raw representation
    instead).
    """
    if schema_size(schema) != len(payload):
        return {}, False
    try:
        data = _decode_struct(schema, payload, 0)
        ok = _encode_struct(schema, data) == payload
    except (SchemaError, struct.error, KeyError, ValueError):
        return {}, False
    return data, ok
