"""Per-section field schemas for ``.rjs`` chunk payloads.

Each schema tiles a payload into named, typed fields (see :mod:`rjmlt.schema`).
A schema is only ever applied when it reproduces the payload byte-for-byte; if
it does not, the record falls back to the raw-segment representation, so naming
a field wrong can never corrupt a file.

These schemas were recovered from a single, mostly-factory-default reference
file. Field *names* are best-effort interpretations: structural facts (strides,
name fields, reference arrays, sentinels) are high-confidence, while the meaning
of numeric regions that are zero/at-default throughout the file is provisional.
Such regions are deliberately typed as ``u8a``/``u16a``/``hex`` rather than
given confident labels. See ``FORMAT.md`` for the confidence notes.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from .schema import schema_size

# --------------------------------------------------------------------------- #
# RJMP -- preset (1964 bytes)                                                  #
# --------------------------------------------------------------------------- #
# name | refs | label table | reserved | controller blocks | small list |
# 8x "Ext Switch" blocks (128 B) | step table | sentinels | 8x scene names.
_EXT_SWITCH = [
    ("lead",        "u8a", 12),    # zeros before the name
    ("name",        "str", 36),    # "Ext Switch N"
    ("params",      "u16a", 40),   # config; default [1,1,0,...]
]
_SCENE = [
    ("name",        "str", 16),    # "Scene 1".."Scene 8"
]
SCHEMA_RJMP = [
    ("name",            "str", 32),    # preset name
    ("field_32",        "u16"),        # 0
    ("ref_song",        "u16"),        # 0x0FFE default (special/global ref)
    ("label_table",     "u8a", 32),    # editable 32-byte field (default = index)
    ("reserved_68",     "u8a", 60),
    ("controllers",     "u8a", 400),   # expression/controller assignment blocks
    ("list_528",        "u8a", 176),   # small index list + padding
    ("ext_switches",    "array", 8, _EXT_SWITCH),
    ("reserved_1728",   "u8a", 28),
    ("step_table",      "u8a", 16),    # 0x01,0x09,...,0x79 default ramp
    ("reserved_1772",   "u8a", 32),
    ("sentinel_1804",   "u8a", 32),    # 0xFF filled
    ("scenes",          "array", 8, _SCENE),
]

# --------------------------------------------------------------------------- #
# RJMs -- song (4032 = 63 x 64 bytes)                                          #
# --------------------------------------------------------------------------- #
_SONG = [
    ("name",        "str", 30),
    ("ref",         "u16"),        # 0x0FFE default
    ("preset_refs", "u16a", 16),   # preset slots, 0xFFFF = empty
]
SCHEMA_RJMs = [
    ("songs", "array", 63, _SONG),
]

# --------------------------------------------------------------------------- #
# RJMS -- setlist (232 bytes)                                                  #
# --------------------------------------------------------------------------- #
SCHEMA_RJMS = [
    ("name",      "str", 32),
    ("song_refs", "u16a", 100),    # song slots, 0x0FFF = empty
]

# --------------------------------------------------------------------------- #
# RJMB -- button page (2576 bytes)                                             #
# --------------------------------------------------------------------------- #
_BUTTON = [
    ("label",      "str", 16),     # short name shown on the switch
    ("name2",      "str", 16),     # secondary copy of label (when customised)
    ("func_type",  "u16"),         # 1=Preset 2=IA/Fn 3=BankDn 4=BankUp 5=PageUp 6=IAStore
    ("params",     "u16a", 8),     # function-dependent parameters
    ("target_ref", "u16"),         # reference handle into another section
    ("reserved",   "hex", 76),     # always zero
]
SCHEMA_RJMB = [
    ("buttons",      "array", 16, _BUTTON),
    ("ext_switches", "array", 4,  _BUTTON),
    ("page_name",    "str", 16),
]

# --------------------------------------------------------------------------- #
# RJMC -- device (3328 = 208 x 16 bytes)                                       #
# --------------------------------------------------------------------------- #
_DEVICE_SLOT = [
    ("ctrl", "u8"),                # 0x04 on populated slots, 0 on empty
    ("name", "str", 15),           # "Step 1"..
]
SCHEMA_RJMC = [
    ("slots", "array", 208, _DEVICE_SLOT),
]

# --------------------------------------------------------------------------- #
# RJMX -- sysex name directory (4064 = 127 x 32 bytes)                         #
# --------------------------------------------------------------------------- #
SCHEMA_RJMX = [
    ("sysex", "array", 127, [("name", "str", 32)]),
]

# --------------------------------------------------------------------------- #
# RJMM -- macro (172 bytes)                                                    #
# --------------------------------------------------------------------------- #
SCHEMA_RJMM = [
    ("name", "str", 32),
    ("body", "u8a", 140),          # step/config data (default-zero in reference)
]

# --------------------------------------------------------------------------- #
# RJME -- expression-pedal block (68 bytes)                                    #
# --------------------------------------------------------------------------- #
SCHEMA_RJME = [
    ("flag0",     "u8"),
    ("assign_id", "u8"),           # expression-assignment id (07 in defaults)
    ("pad2",      "u8a", 4),
    ("max_val",   "u8"),           # 0x7F (MIDI max)
    ("zero7",     "u8a", 39),
    ("ref",       "u16"),          # 0xFFFF unassigned
    ("zero48",    "u8a", 2),
    ("max2",      "u8"),           # 0x7F
    ("zero51",    "u8"),
    ("name",      "str", 16),      # "Exp Pedal N"
]

# --------------------------------------------------------------------------- #
# RJMG -- globals (3 records of different shapes, dispatched by index)         #
# --------------------------------------------------------------------------- #
SCHEMA_RJMG_0 = [   # index 0, 2568 bytes -- main settings
    ("hdr_00",        "u8"),
    ("device_model",  "u8"),
    ("setting_02",    "u8"),
    ("hdr_03",        "u8a", 2),
    ("setting_05",    "u8"),
    ("setting_06",    "u8"),
    ("hdr_07",        "u8"),
    ("flag_08",       "u8"),
    ("setting_09",    "u8"),
    ("setting_0a",    "u8"),
    ("hdr_0b",        "u8"),
    ("flag_0c",       "u8"),
    ("hdr_0d",        "u8a", 3),
    ("setting_10",    "u16"),
    ("settings_012",  "u8a", 62),
    ("exp_pedals",    "array", 3, [("name", "str", 16), ("data", "u8a", 52)]),
    ("exp_pedal_4_name", "str", 16),
    ("exp_pedal_4_data", "u8a", 48),
    ("megx_name",     "str", 16),
    ("megx_data",     "u8a", 32),
    ("loop_slots",    "array", 30, [("flag", "u8"), ("rest", "u8a", 31)]),
    ("settings_block", "u8a", 52),
    ("zeros_1",       "u8a", 1012),
    ("curve_table_1", "u8a", 64),
    ("zeros_2",       "u8a", 32),
    ("curve_table_2", "u8a", 16),
    ("zeros_3",       "u8a", 24),
    ("trailer",       "u8a", 12),
]
SCHEMA_RJMG_1 = [   # index 1, 2048 bytes -- group definitions
    ("groups", "array", 16, [("name", "str", 16), ("params", "u8a", 112)]),
]
SCHEMA_RJMG_2 = [   # index 2, 528 bytes -- routing/loop names
    ("routing_names", "array", 33, [("name", "str", 16)]),
]

# --------------------------------------------------------------------------- #
# Registry                                                                     #
# --------------------------------------------------------------------------- #
_BY_TAG = {
    "RJMP": SCHEMA_RJMP,
    "RJMs": SCHEMA_RJMs,
    "RJMS": SCHEMA_RJMS,
    "RJMB": SCHEMA_RJMB,
    "RJMC": SCHEMA_RJMC,
    "RJMX": SCHEMA_RJMX,
    "RJMM": SCHEMA_RJMM,
    "RJME": SCHEMA_RJME,
}
_RJMG_BY_INDEX = {0: SCHEMA_RJMG_0, 1: SCHEMA_RJMG_1, 2: SCHEMA_RJMG_2}


def get_schema(tag: str, index: int = 0) -> Optional[Sequence]:
    """Return the field schema for a record, or ``None`` if there is none.

    RJMG has three differently shaped records dispatched by ``index``.
    """
    if tag == "RJMG":
        return _RJMG_BY_INDEX.get(index)
    return _BY_TAG.get(tag)


# Self-check at import time: every schema must have a fixed byte size.
for _name, _sch in list(_BY_TAG.items()) + [
    ("RJMG0", SCHEMA_RJMG_0), ("RJMG1", SCHEMA_RJMG_1), ("RJMG2", SCHEMA_RJMG_2)
]:
    schema_size(_sch)  # raises on a malformed schema
