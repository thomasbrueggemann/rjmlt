# RJM Mastermind LT `.rjs` format notes

Reverse-engineered from a real settings file (1157 chunks). This documents the
container, the checksum, and the per-section payload schemas. Confidence is
called out honestly: structural facts (strides, name fields, reference arrays,
sentinels) are solid; the meaning of numeric regions that sit at their factory
default throughout the reference file is **provisional** and such bytes are
typed as `u8a`/`u16a`/`hex` rather than given confident labels.

## Container

A flat sequence of chunks, each a 16-byte header + payload, packed to EOF:

| off | size | field    | notes                                       |
|----:|-----:|----------|---------------------------------------------|
| 0   | 4    | tag      | ASCII, e.g. `RJMP`                          |
| 4   | 4    | version  | u32 LE, `17`                                |
| 8   | 4    | checksum | u32 LE (see below)                          |
| 12  | 2    | length   | u16 LE payload length (always a multiple of 4) |
| 14  | 1    | index    | 0-based record number within the section    |
| 15  | 1    | reserved | 0                                           |
| 16  | len  | payload  |                                             |

## Checksum

**CRC-32/MPEG-2** (poly `0x04C11DB7`, init `0xFFFFFFFF`, no reflection, no final
XOR) over the payload **read as little-endian 32-bit words** (byte-swap each
4-byte group, then forward CRC). Header excluded. Reproduces all 1157 stored
checksums. Implementation: [`rjmlt/checksum.py`](rjmlt/checksum.py).

## Common conventions

- Integers are little-endian; `u16` is the most common field.
- Names are `0x00`-padded Latin-1 strings.
- Reference sentinels: `0xFFFF` empty slot, `0x0FFF` (4095) empty reference,
  `0x0FFE` (4094) a special "global/default" reference.

## Sections

| tag    | type          | count | payload | structure (high-confidence parts) |
|--------|---------------|------:|--------:|-----------------------------------|
| `RJMG` | global        | 3     | 2568/2048/528 | main settings (incl. external-device table) / 16 group slots / 33 routing-point names |
| `RJMB` | button page   | 32    | 2576    | 16 buttons + 4 ext-switch slots (128 B each) + page name |
| `RJMC` | device?       | 16    | 3328    | 208 × 16-byte slots (`ctrl` byte + 15-byte name); see note |
| `RJMs` | song          | 16    | 4032    | 63 songs × 64 B: name(30) + ref + 16 preset slots |
| `RJMS` | setlist       | 64    | 232     | name(32) + 100 song slots (u16, `0x0FFF` empty) |
| `RJMX` | sysex         | 1     | 4064    | 127 × 32-byte name slots |
| `RJMM` | macro         | 128   | 172     | name(32) + 140-byte body |
| `RJME` | expression    | 128   | 68      | params + `name`(16) at offset 52 |
| `RJMP` | preset        | 769   | 1964    | name, refs, label table, controller blocks, 8 ext-switch blocks, step table, 8 scene names |

Every record in the reference file decodes into a schema that re-encodes
byte-exact (1157/1157). The full field schemas live in
[`rjmlt/structures.py`](rjmlt/structures.py).

### `RJMS` setlist (high confidence)
```
name        str   32
song_refs   u16 × 100     # song index, 0x0FFF = empty
```

### `RJMs` song — 63 × 64-byte slots (high confidence)
```
name         str   30
ref          u16           # 0x0FFE default
preset_refs  u16 × 16      # preset index, 0xFFFF = empty
```

### `RJMP` preset (mixed confidence)
```
name           str   32      # high
field_32       u16           # 0 (low)
ref_song       u16           # 0x0FFE default reference (med)
label_table    u8a × 32      # editable text field; default = preset index (med)
reserved_68    u8a × 60      # zero (high)
controllers    u8a × 400     # expression/controller assignment blocks (low semantics)
list_528       u8a × 176     # small index list + padding (low)
ext_switches   8 × 128 B     # each: lead(12) + name(36) + params(u16×40)  (high: names)
reserved_1728  u8a × 28
step_table     u8a × 16      # 0x01,0x09,..,0x79 default ramp (low semantics)
reserved_1772  u8a × 32
sentinel_1804  u8a × 32      # 0xFF
scenes         8 × 16 B      # "Scene 1".."Scene 8" name fields (high)
```

### `RJMB` button page (high confidence on structure)
16 `buttons` + 4 `ext_switches`, each a 128-byte block, then a 16-byte
`page_name`. Block:
```
label       str   16        # switch label (0x0A used as line break)
name2       str   16        # secondary copy of label when customised
func_type   u16             # 1=Preset 2=IA/Fn 3=BankDn 4=BankUp 5=PageUp 6=IAStore
params      u16 × 8         # function-dependent (low semantics)
target_ref  u16             # reference handle into another section (med)
reserved    hex   76        # zero
```

### `RJME` expression block (med confidence)
`assign_id` (07 in defaults; increments 07/08/09/0A when embedded in a preset),
two `0x7F` MIDI-max values, a `ref` (`0xFFFF` unassigned), and a 16-byte `name`
at offset 52.

### `RJMG` globals
Three differently shaped records (dispatched by `index`): main settings
(`index 0`), 16 × 128-byte group slots (`index 1`), and 33 × 16-byte
routing-point names (`index 2`, e.g. Loop 1-16, Buffers, Inputs, Outputs, Tuner
Out, Inserts, Fn Switches, Dry Mix). Numeric settings in `index 0` include a
plausible `440` (tuner reference) and response/curve lookup tables; these are
typed as byte arrays pending confirmation.

The **external-device table** lives in `index 0` at offset 348: 16 fixed slots
of 32 bytes, each `name`(16) + 16 settings bytes. Confirmed against a configured
file (slot 0 `Collider`: `max_pc` 127, `num_presets` 128; slot 1 `M5`). The
remaining settings bytes (MIDI channel, PC offset, port, bank type, flags,
manufacturer/model ids) stay a provisional byte array. This — not the `RJMC`
section — is where the editor's Devices tab is stored.

> **`RJMC` note.** `RJMC` was originally guessed to be the device section
> because the LT has 16 external-device slots, but in a configured file its 16
> records carry an unrelated 208 × `Step N` table while the real device config
> (names + settings) sits in `RJMG` `index 0` as above. The meaning of the
> `RJMC` `Step N` slots is not yet identified; the bytes round-trip regardless.

## What is *not* yet pinned down

A second, user-configured file (`tests/data/thomas.rjs`, the "example1"
reference: named devices, presets, songs, setlists and their wiring) was used to
confirm the structural fields against the editor's own screenshots — names,
references, the device table, scene/ext-switch names, song↔preset and
setlist↔song wiring all decode to the displayed values, and **every chunk
(1157/1157) decodes into named fields with no raw-segment fallback**.

Still provisional, because even the configured file leaves them sparse or
ambiguous: the per-device settings bytes (channel/port/bank/flags), preset
**On/Off colours** and **PC-message / preset-action** blocks (located inside the
preset `label_table` / `controllers` / `list_528` regions — they demonstrably
change when configured, but their exact layout needs more examples to pin
without guessing), macro bodies, and most numeric global settings. These are
preserved losslessly as typed numeric fields; adding more configured files lets
the first differing byte pin each remaining field — the schema engine makes that
an incremental, safe refinement.

### A note on the `str` field type

A fixed-width name field is normally `text` + `0x00` padding and decodes to a
plain string. When non-zero bytes follow the terminator (e.g. a Preset button
whose label keeps a secondary `" 1"` run after the name), the field decodes to
`{"text": "...", "extra": "<hex>"}` instead, so it still re-encodes byte-exact
rather than dropping the tail. Either way the round-trip is lossless.
