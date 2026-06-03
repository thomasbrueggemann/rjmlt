"""The headline guarantee: rjs -> json -> rjs -> json is identity."""

import json

from rjmlt import RjsFile
from rjmlt.segments import decode_payload, encode_segments


def test_tlv_walks_to_eof(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    # Re-serializing with the *stored* checksums must reproduce the file exactly,
    # proving the TLV walk consumed every byte with nothing left over.
    assert rjs.to_bytes(recompute_checksums=False) == sample_bytes


def test_byte_exact_rebuild_with_recomputed_checksums(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    assert rjs.to_bytes(recompute_checksums=True) == sample_bytes


def test_segment_codec_is_inverse(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    for rec in rjs.records:
        assert encode_segments(decode_payload(rec.payload)) == rec.payload


def test_json_roundtrip_identity(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)

    json1 = rjs.to_json()
    rebuilt = RjsFile.from_json(json1)
    rebuilt_bytes = rebuilt.to_bytes()
    json2 = RjsFile.from_bytes(rebuilt_bytes).to_json()

    # The two JSON documents are byte-for-byte identical...
    assert json1 == json2
    # ...and structurally identical (key order independent).
    assert json.loads(json1) == json.loads(json2)
    # ...and the intermediate .rjs is byte-exact too.
    assert rebuilt_bytes == sample_bytes


def test_dict_roundtrip(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    assert RjsFile.from_dict(rjs.to_dict()).to_bytes() == sample_bytes


def test_names_are_exposed(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    assert rjs.by_tag("RJMP")[0].name == "Preset 1"
    assert rjs.by_tag("RJMS")[0].name == "Setlist 1"
    assert rjs.by_tag("RJMs")[0].name == "Song 1"
    assert rjs.by_tag("RJMM")[0].name == "Macro 0"


def test_edit_name_then_roundtrip(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    rjs.by_tag("RJMP")[0].set_name("My Solo")

    data = rjs.to_bytes()
    reloaded = RjsFile.from_bytes(data)

    assert reloaded.by_tag("RJMP")[0].name == "My Solo"
    assert reloaded.invalid_checksums == []
    # Payload length (and therefore the whole file length) is preserved.
    assert len(data) == len(sample_bytes)


def test_edit_preserves_other_records(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    original = {i: r.payload for i, r in enumerate(rjs.records)}
    target = rjs.by_tag("RJMP")[5]
    target_idx = rjs.records.index(target)
    target.set_name("Changed")
    for i, r in enumerate(rjs.records):
        if i == target_idx:
            assert r.payload != original[i]
        else:
            assert r.payload == original[i]


def test_set_name_rejects_too_long(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    rec = rjs.by_tag("RJMP")[0]
    import pytest

    with pytest.raises(ValueError):
        rec.set_name("x" * 500)
