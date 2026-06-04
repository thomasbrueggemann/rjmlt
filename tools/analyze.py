"""Helpers for reverse-engineering .rjs payload schemas.

    from tools.analyze import records_for, verify_schema, hexdump

    schema = [("name","str",34), ("rest","hex",1930)]
    verify_schema("RJMP", schema)   # -> prints pass/fail across all records
"""

import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rjmlt.schema import decode, schema_size  # noqa: E402

_HEADER = struct.Struct("<4sIIHBB")


def _default_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(here, "..", "tests", "data", "test.rjs")


def all_records(path=None):
    data = open(path or _default_path(), "rb").read()
    off, out = 0, []
    while off < len(data):
        tag, ver, chk, plen, idx, rsv = _HEADER.unpack_from(data, off)
        payload = data[off + 16:off + 16 + plen]
        out.append(dict(tag=tag.decode("latin-1"), ver=ver, idx=idx,
                        rsv=rsv, chk=chk, plen=plen, payload=payload))
        off += 16 + plen
    return out


def records_for(tag, path=None):
    return [r for r in all_records(path) if r["tag"] == tag]


def verify_schema(tag, schema, path=None, verbose=True):
    """Check that `schema` decodes+re-encodes every `tag` record byte-exactly."""
    recs = records_for(tag, path)
    if not recs:
        print(f"no records for {tag}")
        return False
    size = schema_size(schema)
    plens = {r["plen"] for r in recs}
    ok = 0
    first_fail = None
    for r in recs:
        data, good = decode(schema, r["payload"])
        if good:
            ok += 1
        elif first_fail is None:
            first_fail = r["idx"]
    if verbose:
        print(f"{tag}: schema_size={size} payload_lens={sorted(plens)} "
              f"verified {ok}/{len(recs)} byte-exact"
              + (f" (first fail idx={first_fail})" if first_fail is not None else ""))
    return ok == len(recs)


def hexdump(payload, base=0, end=None, width=16, collapse=True):
    end = end or len(payload)
    prev, rep, o = None, 0, base
    while o < end:
        chunk = bytes(payload[o:o + width])
        if collapse and chunk == prev:
            rep += 1
            o += width
            continue
        if rep:
            print(f"        ... x{rep} identical ...")
            rep = 0
        prev = chunk
        hx = " ".join(f"{b:02x}" for b in chunk)
        tx = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        print(f"  {o:5d} {hx:<{width * 3}} {tx}")
        o += width
    if rep:
        print(f"        ... x{rep} identical ...")


if __name__ == "__main__":
    for r in all_records():
        pass
    from collections import Counter
    c = Counter((r["tag"], r["plen"]) for r in all_records())
    for (tag, plen), n in sorted(c.items()):
        print(f"{tag} plen={plen} x{n}")
