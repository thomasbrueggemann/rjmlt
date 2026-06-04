"""Structured field decoding: every record, and it stays lossless."""

import pytest

from rjmlt import RjsFile, decode_fields, encode_fields, get_schema
from rjmlt.schema import schema_size


def test_every_record_decodes_to_fields(sample_bytes):
    """All 1157 records in the reference file have an exact structured schema."""
    rjs = RjsFile.from_bytes(sample_bytes)
    no_fields = [(r.tag, r.index) for r in rjs.records if r.fields is None]
    assert no_fields == [], f"records without structured fields: {no_fields[:10]}"


def test_structured_schema_is_exact_inverse(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    for r in rjs.records:
        schema = get_schema(r.tag, r.index)
        data, ok = decode_fields(schema, r.payload)
        assert ok, f"{r.tag}#{r.index} schema not byte-exact"
        assert encode_fields(schema, data) == r.payload


def test_json_uses_fields_not_segments(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    d = rjs.to_dict()
    assert all("fields" in rec for rec in d["records"])
    assert all("segments" not in rec for rec in d["records"])


def test_full_structured_roundtrip_identity(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    json1 = rjs.to_json()
    rebuilt = RjsFile.from_json(json1)
    assert rebuilt.to_bytes() == sample_bytes
    assert RjsFile.from_bytes(rebuilt.to_bytes()).to_json() == json1


def test_reference_array_semantics(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    setlist = rjs.by_tag("RJMS")[0].fields
    assert setlist["name"] == "Setlist 1"
    assert len(setlist["song_refs"]) == 100
    assert all(ref == 0x0FFF for ref in setlist["song_refs"])  # all empty

    song = rjs.by_tag("RJMs")[0].fields["songs"][0]
    assert song["name"] == "Song 1"
    assert len(song["preset_refs"]) == 16
    assert all(ref == 0xFFFF for ref in song["preset_refs"])  # all empty


def test_preset_scene_and_ext_switch_names(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    preset = rjs.by_tag("RJMP")[1].fields
    assert [s["name"] for s in preset["scenes"]] == [f"Scene {i}" for i in range(1, 9)]
    assert preset["ext_switches"][0]["name"] == "Ext Switch 1"


def test_schema_sizes_match_payload_lengths(sample_bytes):
    rjs = RjsFile.from_bytes(sample_bytes)
    for r in rjs.records:
        schema = get_schema(r.tag, r.index)
        assert schema_size(schema) == len(r.payload)


def test_edit_field_via_json_then_reencode(sample_bytes):
    """Editing a structured field through the dict produces a valid file."""
    rjs = RjsFile.from_bytes(sample_bytes)
    d = rjs.to_dict()
    # Rename setlist 0 and assign its first song slot to song index 5.
    setlist_rec = next(r for r in d["records"] if r["tag"] == "RJMS" and r["index"] == 0)
    setlist_rec["fields"]["name"] = "Live Set"
    setlist_rec["fields"]["song_refs"][0] = 5

    rebuilt = RjsFile.from_dict(d)
    reloaded = RjsFile.from_bytes(rebuilt.to_bytes())
    sl = reloaded.by_tag("RJMS")[0]
    assert sl.name == "Live Set"
    assert sl.fields["song_refs"][0] == 5
    assert reloaded.invalid_checksums == []


def test_unknown_record_falls_back_to_segments():
    """A record with no schema uses the raw-segment representation losslessly."""
    from rjmlt.model import Record
    rec = Record(tag="RJZZ", version=17, index=0, payload=b"\x01\x02\x03\x04")
    d = rec.to_dict()
    assert "segments" in d and "fields" not in d
    assert Record.from_dict(d).payload == rec.payload
