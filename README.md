# rjmlt

Read and write **RJM Mastermind LT** `.rjs` settings files in Python.

The `.rjs` format is the proprietary binary container the RJM editor uses to
store everything on the controller — presets, songs, setlists, button pages,
macros, expression-pedal blocks and global settings. `rjmlt` parses it into a
clean object model (and a lossless JSON projection), lets you edit names and
bytes, and writes the file back out **with correct checksums**, so you can drive
the footswitch from your own tooling.

```python
from rjmlt import RjsFile

rjs = RjsFile.read("test.rjs")
print(len(rjs), "records")                 # 1157 records
print(rjs.by_tag("RJMP")[0].name)          # "Preset 1"

rjs.by_tag("RJMP")[0].set_name("My Solo")  # rename preset 1
rjs.write("edited.rjs")                    # checksum recomputed automatically
```

## Why this exists

The format is a tagged-chunk container and, with one exception, every field was
transparent. The exception was a per-chunk checksum that no standard CRC matched.
It turned out to be **CRC-32/MPEG-2 computed over the payload read as
little-endian 32-bit words** — recovered by differential analysis across all
1157 chunks of a real file (see [below](#the-checksum)). Because the checksum is
solved, `rjmlt` can produce files the device accepts after you edit them, not
just read existing ones.

## Install

```bash
pip install -e .          # from a checkout
pip install -e ".[test]"  # with pytest
```

No runtime dependencies; Python 3.8+.

## Lossless round-trip

The headline guarantee, enforced by the test suite:

```
.rjs  ->  JSON  ->  .rjs  ->  JSON
```

is the identity. Decoding then re-encoding reproduces the original file
**byte-for-byte**, and the JSON taken before and after is identical. This holds
because each chunk payload is represented as an ordered tiling of segments where
every byte lands in exactly one segment, so `encode(decode(payload)) == payload`
by construction.

```python
rjs = RjsFile.read("test.rjs")
assert RjsFile.from_json(rjs.to_json()).to_bytes() == rjs.to_bytes()
```

## Command line

```bash
python -m rjmlt info   test.rjs            # summary + checksum validation
python -m rjmlt decode test.rjs -o out.json
python -m rjmlt encode out.json  -o rebuilt.rjs   # byte-identical to test.rjs
```

(`rjmlt` is also installed as a console script.)

## The file format

A `.rjs` file is a flat sequence of self-describing chunks (a TLV container)
that walks cleanly to EOF with no padding. Each chunk is a 16-byte header
followed by its payload:

| offset | size | field      | notes                                            |
|-------:|-----:|------------|--------------------------------------------------|
| `+0`   | 4    | `tag`      | 4 ASCII bytes, e.g. `RJMP` (case-sensitive)      |
| `+4`   | 4    | `version`  | u32 LE — `17` for current firmware               |
| `+8`   | 4    | `checksum` | u32 LE — CRC of the payload (see below)           |
| `+12`  | 2    | `length`   | u16 LE — payload length in bytes (multiple of 4) |
| `+14`  | 1    | `index`    | 0-based record number within its section         |
| `+15`  | 1    | `reserved` | `0`                                              |
| `+16`  | len  | `payload`  | the record body                                  |

### Sections

The tags map onto the LT's published capacities, which is how you know the read
is correct:

| tag    | type          | count | meaning                                |
|--------|---------------|------:|----------------------------------------|
| `RJMG` | `global`      | 3     | global settings (main / loops / routing) |
| `RJMB` | `button_page` | 32    | button pages                           |
| `RJMC` | `device`      | 16    | external devices                       |
| `RJMs` | `song`        | 16    | song blocks (63 songs × 64 B each)     |
| `RJMS` | `setlist`     | 64    | setlists                               |
| `RJMX` | `sysex`       | 1     | sysex table (127 × 32 B slots)         |
| `RJMM` | `macro`       | 128   | macros                                 |
| `RJME` | `expression`  | 128   | expression-pedal blocks                |
| `RJMP` | `preset`      | 769   | presets (768 + 1 "Global Preset")      |

Names are stored as zero-padded Latin-1 strings inside the payloads (e.g.
`Preset 1`, `Setlist 1`, `Song 1`). `rjmlt` surfaces them as `record.name` /
`record.names` and lets you edit them with `record.set_name(...)`, which keeps
the field width fixed so the rest of the record is untouched.

### The checksum

The one field that needed cracking. It is:

> **CRC-32/MPEG-2** — polynomial `0x04C11DB7`, init `0xFFFFFFFF`, no input or
> output reflection, no final XOR — computed over the payload **read as
> little-endian 32-bit words** (equivalently: byte-swap each 4-byte group, then
> run a plain forward CRC-32/MPEG-2). The 16-byte header is **not** included.

```python
from rjmlt import compute_checksum
compute_checksum(record.payload) == record.stored_checksum   # True for every chunk
```

This reproduces the stored checksum for all 1157 chunks in the reference file.
How it was found: the checksum is linear over GF(2), so XOR-ing one payload byte
XORs the checksum by a value that depends only on `(position, delta)` — the
signature of a CRC. The effect of a single-byte change three bytes from the end
of a chunk came out as exactly `0x04C11DB7`, and the way the effect "moved" as
the byte position shifted revealed that bytes are consumed in little-endian
32-bit-word order. `init`/`xorout` were then solved by linear algebra.

## JSON shape

```json
{
  "format": "rjm-mastermind-lt",
  "json_version": 1,
  "records": [
    {
      "tag": "RJMP",
      "type": "preset",
      "version": 17,
      "index": 0,
      "reserved": 0,
      "stored_checksum": 1612668609,
      "segments": [
        { "text": "Preset 1" },
        { "raw": "0000000000000000....fe0f...." }
      ]
    }
  ]
}
```

`text` segments are printable runs (names); `raw` segments are everything not
yet decoded, preserved verbatim as hex. Editing a `text` value and re-encoding
yields a valid file.

## Python API

```python
from rjmlt import RjsFile, Record, compute_checksum

rjs = RjsFile.read("test.rjs")          # or RjsFile.from_bytes(b)
rjs.records                              # list[Record]
rjs.by_tag("RJMS")                       # all setlists
rjs.invalid_checksums                    # records whose checksum doesn't verify

rec = rjs.by_tag("RJMP")[0]
rec.name, rec.names                      # decoded name(s)
rec.type                                 # "preset"
rec.checksum_valid                       # True
rec.set_name("Lead Boost")               # edit a name (fixed width preserved)
rec.replace_bytes(0x22, b"\x01")         # low-level byte edit

rjs.to_bytes()                           # bytes, checksums recomputed
rjs.to_json()                            # str
rjs.write("out.rjs")
RjsFile.from_json(text)                  # parse JSON back
```

## Tests

```bash
pytest
```

The suite verifies the TLV walk reaches EOF, that every stored checksum is
reproduced, that the segment codec is a true inverse, that `.rjs → JSON → .rjs →
JSON` is the identity, and that editing a name produces a byte-length-preserving
file with a valid checksum.

## Status & limitations

- ✅ Lossless read/write, byte-exact round-trip, correct checksums, editable names.
- 🚧 The numeric meaning of most payload bytes (MIDI messages, routing, scene
  assignments) is preserved verbatim but not yet decoded into named fields.
  Contributions welcome — the `raw` segments are where that work goes.
- The reference file targets firmware/editor format `version 17`.

## License

MIT — see [LICENSE](LICENSE).

> Not affiliated with or endorsed by RJM Music Technology. "Mastermind LT" is a
> trademark of its respective owner. This is an independent, clean-room format
> description for interoperability.
