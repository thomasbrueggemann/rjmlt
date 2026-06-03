"""The cracked CRC must reproduce every stored checksum, and survive edits."""

import struct

import pytest

from rjmlt import RjsFile, compute_checksum
from rjmlt.checksum import INIT, POLYNOMIAL


def test_known_parameters():
    assert POLYNOMIAL == 0x04C11DB7
    assert INIT == 0xFFFFFFFF


def test_all_stored_checksums_match(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    bad = rjs.invalid_checksums
    assert bad == [], f"{len(bad)} records have a checksum our formula misses"
    assert len(rjs) == 1157


def test_checksum_requires_multiple_of_four():
    with pytest.raises(ValueError):
        compute_checksum(b"\x00\x00\x00")


def test_first_record_checksum(sample_bytes):
    # The very first chunk header stores its checksum at offset +8.
    stored = struct.unpack_from("<I", sample_bytes, 8)[0]
    plen = struct.unpack_from("<H", sample_bytes, 12)[0]
    payload = sample_bytes[16:16 + plen]
    assert compute_checksum(payload) == stored


def test_checksum_changes_after_edit(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    rec = rjs.by_tag("RJMP")[0]
    before = rec.computed_checksum
    rec.set_name("Edited")
    assert rec.computed_checksum != before
    # And a freshly written+reloaded file validates against the new checksum.
    reloaded = RjsFile.from_bytes(rjs.to_bytes())
    assert reloaded.invalid_checksums == []
