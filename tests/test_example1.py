"""Ground-truth extraction test against a real, user-configured file.

``tests/data/thomas.rjs`` is the "example1" reference: a file saved from the RJM
Mastermind editor with named devices, presets, songs, setlists and the wiring
between them.  Every assertion below corresponds to a value visible in the
editor screenshots in ``example1/``.  Together with the round-trip identity this
proves the library parses *actual* values, not just factory defaults.
"""

import json

from rjmlt import RjsFile


# --------------------------------------------------------------------------- #
# The headline guarantee on a configured file: rjs -> json -> rjs -> json      #
# --------------------------------------------------------------------------- #
def test_configured_roundtrip_identity(configured_bytes):
    rjs = RjsFile.from_bytes(configured_bytes)

    json1 = rjs.to_json()
    rebuilt_bytes = RjsFile.from_json(json1).to_bytes()
    json2 = RjsFile.from_bytes(rebuilt_bytes).to_json()

    # rjs -> json -> rjs is byte-exact ...
    assert rebuilt_bytes == configured_bytes
    # ... and the JSON before and after is identical (string and structurally).
    assert json1 == json2
    assert json.loads(json1) == json.loads(json2)
    assert rjs.invalid_checksums == []


def test_every_record_decodes_into_named_fields(configured_bytes):
    # Not just lossless: every chunk in this configured file decodes into a
    # named-field schema (no raw-segment fallbacks).
    rjs = RjsFile.from_bytes(configured_bytes)
    assert all(r.fields is not None for r in rjs.records)
    assert len(rjs) == 1157


# --------------------------------------------------------------------------- #
# Devices tab: Device 1 "Collider", Device 2 "M5", rest empty                  #
# --------------------------------------------------------------------------- #
def test_devices_tab(configured_bytes):
    rjs = RjsFile.from_bytes(configured_bytes)
    devices = rjs.by_tag("RJMG")[0].fields["devices"]

    assert devices[0]["name"] == "Collider"
    assert devices[1]["name"] == "M5"
    assert [d["name"] for d in devices[2:]] == [""] * 14  # devices 3..16 empty

    # Collider's settings as shown in the editor.
    assert devices[0]["max_pc"] == 127        # "Max PC: 127"
    assert devices[0]["num_presets"] == 128    # "# of Presets: 128"


# --------------------------------------------------------------------------- #
# Presets tab: 1 "Clean", 4 "Pitch", and the "Global Preset"                   #
# --------------------------------------------------------------------------- #
def test_presets_tab(configured_bytes):
    rjs = RjsFile.from_bytes(configured_bytes)
    presets = rjs.by_tag("RJMP")

    # Editor preset N (1-based, after "Global") == array index N-1.
    assert presets[0].fields["name"] == "Clean"
    assert presets[1].fields["name"] == "Preset 2"
    assert presets[3].fields["name"] == "Pitch"
    assert presets[768].fields["name"] == "Global Preset"

    # Scene names are surfaced as named fields.
    assert [s["name"] for s in presets[0].fields["scenes"]] == [
        f"Scene {i}" for i in range(1, 9)
    ]


# --------------------------------------------------------------------------- #
# Songs tab: named songs and the preset wired into song 1                      #
# --------------------------------------------------------------------------- #
def test_songs_tab(configured_bytes):
    rjs = RjsFile.from_bytes(configured_bytes)
    presets = rjs.by_tag("RJMP")
    songs = rjs.by_tag("RJMs")[0].fields["songs"]

    expected = [
        "Nothing To Declare", "Something In Between Us", "Wasted", "Hive",
        "Miracle", "Horses", "Dreams", "Hold You", "Shadow",
    ]
    assert [s["name"] for s in songs[: len(expected)]] == expected
    assert songs[9]["name"] == "Song 10"  # unnamed songs keep the default name

    # Song 1 "Nothing To Declare" has exactly one preset: "Clean".
    song1_refs = [r for r in songs[0]["preset_refs"] if r != 0xFFFF]
    assert song1_refs == [0]
    assert presets[song1_refs[0]].fields["name"] == "Clean"


# --------------------------------------------------------------------------- #
# Setlists tab: "29 May2026" wired to Wasted / Something In Between Us / Hive  #
# --------------------------------------------------------------------------- #
def test_setlists_tab(configured_bytes):
    rjs = RjsFile.from_bytes(configured_bytes)
    setlist = rjs.by_tag("RJMS")[0].fields
    songs = rjs.by_tag("RJMs")[0].fields["songs"]

    assert setlist["name"] == "29 May2026"  # stored without a space before 2026

    refs = [r for r in setlist["song_refs"] if r != 0x0FFF]
    assert refs == [2, 1, 3]
    assert [songs[r]["name"] for r in refs] == [
        "Wasted", "Something In Between Us", "Hive",
    ]


# --------------------------------------------------------------------------- #
# Button page: a configured page decodes into named fields (no fallback), with #
# the secondary run after the label preserved losslessly.                      #
# --------------------------------------------------------------------------- #
def test_configured_button_page_decodes(configured_bytes):
    rjs = RjsFile.from_bytes(configured_bytes)
    page = next(p for p in rjs.by_tag("RJMB") if p.index == 0).fields

    assert page is not None  # used to fall back to raw segments
    assert page["buttons"][0]["label"] == {"text": "Clean", "extra": "20310000000000000000"}
    assert page["buttons"][1]["label"] == "Preset 2"
    assert page["buttons"][0]["func_type"] == 1  # Preset-type button
