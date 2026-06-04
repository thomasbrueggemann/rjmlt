"""rjmlt -- read and write RJM Mastermind LT ``.rjs`` settings files.

Example
-------
>>> from rjmlt import RjsFile
>>> rjs = RjsFile.read("test.rjs")
>>> presets = rjs.by_tag("RJMP")
>>> presets[0].name
'Preset 1'
>>> presets[0].set_name("My Solo")
>>> rjs.write("edited.rjs")        # checksums are recomputed automatically

The JSON projection round-trips losslessly::

>>> RjsFile.from_json(rjs.to_json()).to_bytes() == rjs.to_bytes()
True
"""

from __future__ import annotations

from .checksum import INIT, POLYNOMIAL, compute_checksum
from .model import HEADER_SIZE, TAG_TYPES, Record, RjsFile
from .schema import decode as decode_fields
from .schema import encode as encode_fields
from .segments import decode_payload, encode_segments
from .structures import get_schema

__version__ = "0.2.0"

__all__ = [
    "RjsFile",
    "Record",
    "compute_checksum",
    "decode_payload",
    "encode_segments",
    "decode_fields",
    "encode_fields",
    "get_schema",
    "TAG_TYPES",
    "HEADER_SIZE",
    "POLYNOMIAL",
    "INIT",
    "__version__",
]
