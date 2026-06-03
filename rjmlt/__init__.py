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
from .segments import decode_payload, encode_segments

__version__ = "0.1.0"

__all__ = [
    "RjsFile",
    "Record",
    "compute_checksum",
    "decode_payload",
    "encode_segments",
    "TAG_TYPES",
    "HEADER_SIZE",
    "POLYNOMIAL",
    "INIT",
    "__version__",
]
