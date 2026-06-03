"""Command-line conversion between ``.rjs`` and JSON.

Usage::

    python -m rjmlt decode test.rjs -o test.json
    python -m rjmlt encode test.json -o rebuilt.rjs
    python -m rjmlt info   test.rjs
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from . import RjsFile, __version__


def _decode(args) -> int:
    rjs = RjsFile.read(args.input)
    text = rjs.to_json(indent=None if args.compact else 2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        sys.stdout.write(text + "\n")
    return 0


def _encode(args) -> int:
    with open(args.input, "r", encoding="utf-8") as fh:
        rjs = RjsFile.from_json(fh.read())
    data = rjs.to_bytes()
    out = args.output or "out.rjs"
    with open(out, "wb") as fh:
        fh.write(data)
    sys.stderr.write(f"wrote {len(data)} bytes to {out}\n")
    return 0


def _info(args) -> int:
    rjs = RjsFile.read(args.input)
    counts = Counter(r.tag for r in rjs.records)
    print(f"records: {len(rjs)}")
    for tag, count in sorted(counts.items()):
        from .model import TAG_TYPES

        print(f"  {tag} ({TAG_TYPES.get(tag, 'unknown'):11}) x{count}")
    bad = rjs.invalid_checksums
    print(f"checksums: {len(rjs) - len(bad)}/{len(rjs)} valid")
    if bad:
        print("  invalid:", ", ".join(f"{r.tag}#{r.index}" for r in bad[:10]))
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="rjmlt", description=__doc__)
    parser.add_argument("--version", action="version", version=f"rjmlt {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_decode = sub.add_parser("decode", help="convert .rjs to JSON")
    p_decode.add_argument("input")
    p_decode.add_argument("-o", "--output")
    p_decode.add_argument("--compact", action="store_true", help="no indentation")
    p_decode.set_defaults(func=_decode)

    p_encode = sub.add_parser("encode", help="convert JSON back to .rjs")
    p_encode.add_argument("input")
    p_encode.add_argument("-o", "--output")
    p_encode.set_defaults(func=_encode)

    p_info = sub.add_parser("info", help="summarize a .rjs file")
    p_info.add_argument("input")
    p_info.set_defaults(func=_info)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
