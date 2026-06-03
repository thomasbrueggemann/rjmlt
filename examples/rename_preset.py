"""Minimal example: rename a preset and write a device-valid file.

    python examples/rename_preset.py tests/data/test.rjs
"""

import sys

from rjmlt import RjsFile


def main(path: str) -> None:
    rjs = RjsFile.read(path)

    presets = rjs.by_tag("RJMP")
    print(f"Loaded {len(rjs)} records, {len(presets)} presets")
    print("First five preset names:", [p.name for p in presets[:5]])

    presets[0].set_name("Lead Boost")
    presets[1].set_name("Clean Verb")

    out = "edited.rjs"
    rjs.write(out)

    check = RjsFile.read(out)
    assert check.invalid_checksums == [], "checksums must validate"
    print("Wrote", out, "->", [p.name for p in check.by_tag('RJMP')[:5]])


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "tests/data/test.rjs")
