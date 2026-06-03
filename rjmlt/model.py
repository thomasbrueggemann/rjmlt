"""Object model for an RJM Mastermind LT ``.rjs`` settings file.

The file is a flat sequence of self-describing chunks (a tagged TLV container).
Each chunk has a fixed 16-byte header followed by its payload::

    offset  size  field
    +0      4     tag        4 ASCII bytes, e.g. b"RJMP" (case-sensitive)
    +4      4     version    u32 little-endian (17 for current firmware)
    +8      4     checksum   u32 little-endian, CRC-32/MPEG-2 of the payload
                             read as little-endian 32-bit words (see checksum.py)
    +12     2     length     u16 little-endian, payload length in bytes
    +14     1     index      0-based record number within its section
    +15     1     reserved   0
    +16     length          payload

Chunks are stored back to back with no padding and the file ends exactly after
the last chunk's payload.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

from .checksum import compute_checksum
from .segments import (
    MIN_TEXT_RUN,
    Segment,
    decode_payload,
    encode_segments,
)

__all__ = ["Record", "RjsFile", "TAG_TYPES", "HEADER_SIZE"]

HEADER_SIZE = 16

#: Human-readable name for each known section tag and its capacity on the LT.
TAG_TYPES: Dict[str, str] = {
    "RJMG": "global",      # global settings (main / audio loops / routing)
    "RJMB": "button_page",
    "RJMC": "device",
    "RJMs": "song",
    "RJMS": "setlist",
    "RJMX": "sysex",
    "RJMM": "macro",
    "RJME": "expression",
    "RJMP": "preset",
}

_HEADER = struct.Struct("<4sIIHBB")


def _is_printable(byte: int) -> bool:
    return 0x20 <= byte < 0x7F


@dataclass
class Record:
    """A single chunk: a typed header plus its payload bytes."""

    tag: str
    version: int
    index: int
    payload: bytes
    reserved: int = 0
    #: Checksum as read from the file; ``None`` for records built from scratch.
    stored_checksum: Optional[int] = None
    #: True once the payload has been modified since it was loaded.
    dirty: bool = False

    # -- derived information -------------------------------------------------

    @property
    def type(self) -> str:
        """Human-readable section type (e.g. ``"preset"``)."""
        return TAG_TYPES.get(self.tag, "unknown")

    @property
    def computed_checksum(self) -> int:
        """The checksum our algorithm produces for the current payload."""
        return compute_checksum(self.payload)

    @property
    def checksum_valid(self) -> bool:
        """Whether the stored checksum matches the computed one."""
        return self.stored_checksum == self.computed_checksum

    # -- name access ---------------------------------------------------------

    def _text_fields(self) -> List[Tuple[int, str]]:
        """Return ``(offset, text)`` for each printable run in the payload."""
        fields: List[Tuple[int, str]] = []
        p = self.payload
        i, n = 0, len(p)
        while i < n:
            j = i
            while j < n and _is_printable(p[j]):
                j += 1
            if j - i >= MIN_TEXT_RUN:
                fields.append((i, p[i:j].decode("latin-1")))
                i = j
            else:
                i += 1
        return fields

    @property
    def names(self) -> List[str]:
        """All embedded names in the payload, in order."""
        return [text for _, text in self._text_fields()]

    @property
    def name(self) -> Optional[str]:
        """The first embedded name, or ``None`` if the payload has none."""
        fields = self._text_fields()
        return fields[0][1] if fields else None

    def set_name(self, value: str, slot: int = 0, width: Optional[int] = None) -> None:
        """Replace the ``slot``-th embedded name with ``value``.

        The name field is treated as a fixed-width, zero-padded Latin-1 field.
        By default the field width is detected from the original name plus its
        trailing ``0x00`` padding; pass ``width`` to override it.  The payload
        length is preserved, so the rest of the record is untouched.
        """
        fields = self._text_fields()
        if slot >= len(fields):
            raise IndexError(f"record has no name slot {slot} (has {len(fields)})")
        offset, old = fields[slot]
        p = bytearray(self.payload)
        if width is None:
            # Field width = name + the run of zero padding that follows it.
            end = offset + len(old)
            while end < len(p) and p[end] == 0x00:
                end += 1
            width = end - offset
        encoded = value.encode("latin-1")
        if len(encoded) > width:
            raise ValueError(
                f"name {value!r} ({len(encoded)} bytes) exceeds field width {width}"
            )
        p[offset:offset + width] = encoded + b"\x00" * (width - len(encoded))
        self.payload = bytes(p)
        self.dirty = True

    def replace_bytes(self, offset: int, data: bytes) -> None:
        """Overwrite ``len(data)`` payload bytes starting at ``offset``."""
        if offset + len(data) > len(self.payload):
            raise ValueError("replacement runs past the end of the payload")
        p = bytearray(self.payload)
        p[offset:offset + len(data)] = data
        self.payload = bytes(p)
        self.dirty = True

    # -- serialization -------------------------------------------------------

    def header_bytes(self, *, recompute_checksum: bool = True) -> bytes:
        """Return the 16-byte header for this record."""
        if recompute_checksum or self.stored_checksum is None or self.dirty:
            checksum = self.computed_checksum
        else:
            checksum = self.stored_checksum
        return _HEADER.pack(
            self.tag.encode("latin-1"),
            self.version,
            checksum,
            len(self.payload),
            self.index,
            self.reserved,
        )

    def to_bytes(self, *, recompute_checksum: bool = True) -> bytes:
        return self.header_bytes(recompute_checksum=recompute_checksum) + self.payload

    def to_dict(self) -> dict:
        return {
            "tag": self.tag,
            "type": self.type,
            "version": self.version,
            "index": self.index,
            "reserved": self.reserved,
            "stored_checksum": self.stored_checksum,
            "segments": decode_payload(self.payload),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Record":
        payload = encode_segments(data["segments"])
        return cls(
            tag=data["tag"],
            version=data["version"],
            index=data["index"],
            reserved=data.get("reserved", 0),
            payload=payload,
            stored_checksum=data.get("stored_checksum"),
            dirty=False,
        )


@dataclass
class RjsFile:
    """A parsed ``.rjs`` file: an ordered list of :class:`Record`."""

    records: List[Record] = field(default_factory=list)
    #: JSON document schema version emitted by :meth:`to_dict`.
    JSON_VERSION = 1
    FORMAT = "rjm-mastermind-lt"

    # -- parsing / building --------------------------------------------------

    @classmethod
    def from_bytes(cls, data: bytes) -> "RjsFile":
        records: List[Record] = []
        off, n = 0, len(data)
        while off < n:
            if off + HEADER_SIZE > n:
                raise ValueError(
                    f"truncated header at offset {off} ({n - off} bytes left)"
                )
            tag, version, checksum, length, index, reserved = _HEADER.unpack_from(
                data, off
            )
            start = off + HEADER_SIZE
            end = start + length
            if end > n:
                raise ValueError(
                    f"chunk at {off} claims {length} payload bytes but only "
                    f"{n - start} remain"
                )
            records.append(
                Record(
                    tag=tag.decode("latin-1"),
                    version=version,
                    index=index,
                    reserved=reserved,
                    payload=data[start:end],
                    stored_checksum=checksum,
                    dirty=False,
                )
            )
            off = end
        return cls(records)

    def to_bytes(self, *, recompute_checksums: bool = True) -> bytes:
        out = bytearray()
        for rec in self.records:
            out += rec.to_bytes(recompute_checksum=recompute_checksums)
        return bytes(out)

    @classmethod
    def read(cls, path) -> "RjsFile":
        with open(path, "rb") as fh:
            return cls.from_bytes(fh.read())

    def write(self, path, *, recompute_checksums: bool = True) -> None:
        with open(path, "wb") as fh:
            fh.write(self.to_bytes(recompute_checksums=recompute_checksums))

    # -- JSON ----------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format": self.FORMAT,
            "json_version": self.JSON_VERSION,
            "records": [rec.to_dict() for rec in self.records],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RjsFile":
        return cls([Record.from_dict(r) for r in data["records"]])

    def to_json(self, *, indent: Optional[int] = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "RjsFile":
        return cls.from_dict(json.loads(text))

    # -- convenience ---------------------------------------------------------

    def by_tag(self, tag: str) -> List[Record]:
        """All records carrying ``tag`` (e.g. ``"RJMP"``)."""
        return [r for r in self.records if r.tag == tag]

    @property
    def invalid_checksums(self) -> List[Record]:
        """Records whose stored checksum does not match the computed one."""
        return [r for r in self.records if not r.checksum_valid]

    def __len__(self) -> int:
        return len(self.records)

    def __iter__(self):
        return iter(self.records)
