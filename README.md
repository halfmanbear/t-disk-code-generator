# T-Disc barcode generator and bitfield laboratory

**Status: experimental protocol research.** Renders six-digit Tassimo T-Disc-style decimal codes using the exact custom optical bar pattern, on a complete (unclipped) PNG canvas. Also supports direct numeric payload inspection, controlled bit mutations, balanced low-two-bit experiments, and auditing of observed code datasets.

Three distinct claims must be kept separate:

1. **Validated arithmetic:** six decimal digits; the final digit is a UPC-style modulo-10 checksum of the previous five.
2. **Implemented field model:** five-bar-per-digit renderer, field assembly order, variable-width `misc` suffix, and `<1000` escape/trimming heuristic. The latter is an encoding rule of this tool, not verified firmware behaviour.
3. **Unverified physical interpretation:** brewing variables, meaning of `misc`/low-order bits, scanner tolerance, and machine-specific handling. Valid checksums and known codes do not establish a reliable field decoder.

See [Evidence and references](#evidence-and-references).

## Requirements

- Python **3.9+**; Pillow: `python -m pip install Pillow`
- No barcode library and no network connection required at runtime.

```sh
python -m pip install Pillow
python t-disk-barcode.py --self-test
```

## Command reference

### Render a verified six-digit decimal code

```sh
python t-disk-barcode.py --code 061780
python t-disk-barcode.py --code 674478 --output chai-milk.png
```

Requires six ASCII digits with a valid check digit. Preferred path when the numeric code is already known; makes no assumptions about brewing fields. Accepts payload values beyond 65 535. Default output: `barcode_<six_digit_code>.png`. Overwrites an existing file of the same name.

### Inspect the checksum-stripped numeric payload

```sh
python t-disk-barcode.py --inspect-code 061780
python t-disk-barcode.py --inspect-code 674478
```

Prints the five-digit decimal payload, its numeric value, minimum bit length, a zero-extended 16/17-bit MSB-first view, an LSB-first display, the two lowest numeric bits, and the number of field-model inputs that produce the code. No image is written. Bit-order display is for inspection only; it does not claim firmware byte order.

### Alter a numeric payload bit

```sh
python t-disk-barcode.py --code 061780 --flip-bit 0
python t-disk-barcode.py --code 061780 --flip-bit 16  # -> 717144
python t-disk-barcode.py --code 061780 --set-low2 0  # -> 061766
```

`--flip-bit N` toggles bit `N` of the unsigned integer formed by the five pre-checksum digits (bit 0 = LSB); indices 0–16. `--set-low2 N` replaces bits 1:0 with the value 0–3. Check digit is always recomputed. Mutations that would leave the five-digit range 0–99 999 are rejected. These are pure numeric mutations, not guaranteed independent firmware controls.

### Generate a balanced low-two-bit experiment

```sh
python t-disk-barcode.py --sweep-low2 061780 \
  --experiment-dir experiments/espresso_01 \
  --repeats 3 --seed 42
```

Produces four PNGs (one per low-two-bit state) and a CSV measurement template `trials.csv`. Three randomized blocks, each containing all four states once (12 planned observations). Fixed seed makes the order reproducible. Output directory must not already exist.

| State | Five-digit payload | Complete code |
| --- | --- | --- |
| `00` | `06176` | `061766` |
| `01` | `06177` | `061773` |
| `10` | `06178` | `061780` (baseline) |
| `11` | `06179` | `061797` |

All four codes differ only in numeric bits 1:0 before check-digit recomputation. The CSV contains planned sequence, encoded state, code, payload, changed bits, PNG filename, and empty columns for machine/revision, disc placement, printer settings, scan result, measured mass, phase timings, outlet temperature and notes. Record observed physical results; do not pre-interpret the bits.

**Experimental controls:** same machine, disc geometry, barcode position, print size/orientation, supply and instruments. Randomize order to limit warm-up and carry-over. Measure mass and dispense phases directly. Control for soak/purge retention. Re-measure a second baseline before assigning meaning to the low bits. Novel codes may be rejected; accepted codes are not automatically safe to run unattended. Do not connect grounded instruments to potentially mains-referenced electronics without isolation.

### Audit a code inventory

```sh
python t-disk-barcode.py --audit-codes published_codes_2013.csv
```

UTF-8 CSV with a `code` column of complete six-digit codes. Validates checksums, counts distinct codes, reports the numeric two-bit histogram and the number of payloads that use bit 16. Invalid rows cause failure rather than silent skew.

The included `published_codes_2013.csv` is a 34-distinct-code convenience sample transcribed from Markus Birth’s September 2013 public list (Professional category excluded). Observed histogram:

| Numeric bits 1:0 | Distinct codes |
| --- | ---: |
| `00` | 0 |
| `01` | 11 |
| `10` | 5 |
| `11` | 18 |

Nine of the 34 payloads require bit 16. Absence of `00` in this non-random sample is a candidate reserved/invalid state worth testing, not a proven protocol property. Do not infer brand, hot/cold mode or extension version from those two bits without physical measurements.

### Field-model generation

```sh
python t-disk-barcode.py
python t-disk-barcode.py \
  --temperature 3 --size 0 --charge 0 \
  --volume 2 --flow-rate 1 --purge 0 --misc 0 --trace
```

The explicit example produces `061780`. This is a software regression vector, not a verified 70 ml espresso recipe. Colliding parameter sets print an alternative selection. `--require-unique` refuses generation when another input combination yields the same code under the same mapping (exit status 2). All seven fields must be supplied together or none (interactive mode).

```sh
python t-disk-barcode.py \
  --temperature 0 --size 0 --charge 0 \
  --volume 0 --flow-rate 0 --purge 0 --misc 1 --require-unique
```

Rejects the colliding code `655378` (also produced by `purge=1, misc=0` with otherwise identical inputs).

`python t-disk-barcode.py --help` lists the complete switch set. Specialized numeric modes, field generation and self-test are mutually exclusive.

## Known versus hypothesized bitfields

### Patent-defined nominal 13-bit fields

US7231869B2 Table 3 lists fields in order: temperature (2), cartridge charge (2), volume (4), flow (3), purge (2). It is an *example* representation of operational variables, not a verified bit-level mapping of deployed decimal barcodes. Extra error-checking bits and a 16-bit code example are also mentioned. Patent position numbering does not define alignment with the five-digit integer.

| Parameter | Values by input index | Status |
| --- | --- | --- |
| Temperature, 2 bits | `00` cold; `01` warm; `10` 83 °C; `11` 93 °C | Patent nominal |
| Charge, 2 bits | `00` fast+soak; `01` fast/no soak; `10` slow+soak; `11` slow/no soak | Patent nominal |
| Volume, 4 bits | see table | Patent nominal; disputed experimentally |
| Flow, 3 bits | `000`–`111` → 30 %–100 % in 10 % steps | Patent nominal |
| Purge, 2 bits | `00` slow/short; `01` slow/long; `10` fast/short; `11` fast/long | Patent nominal |

| Index | Bits | Patent ml | Index | Bits | Patent ml |
| ---: | --- | ---: | ---: | --- | ---: |
| 0 | `0000` | 50 | 8 | `1000` | 150 |
| 1 | `0001` | 60 | 9 | `1001` | 170 |
| 2 | `0010` | 70 | 10 | `1010` | 190 |
| 3 | `0011` | 80 | 11 | `1011` | 210 |
| 4 | `0100` | 90 | 12 | `1100` | 230 |
| 5 | `0101` | 100 | 13 | `1101` | 250 |
| 6 | `0110` | 110 | 14 | `1110` | 275 |
| 7 | `0111` | 130 | 15 | `1111` | 300 |

Physical reverse-engineering has produced results that do not consistently match the four-bit volume table. Do not treat the values above as measured targets or assume temperature is fixed at the patent nominals on a given machine.

### Implemented extras: `size`, `misc`, escape and trim

Fields are concatenated MSB-first:

```text
temperature(2) | size(1) | charge(2) | volume(4) | flow(3) | purge(2) | misc(0..2)
```

- `size`: one bit (0 = regular, 1 = large). Location and meaning unverified against the patent.
- `misc`: variable width. Input 0 appends zero bits, 1 appends `"1"`, 2 appends `"11"`. No fourth state.
- The `<1000` high-bit escape and optional final-bit removal are encoding rules of this implementation; they alter alignment and can collapse distinct input combinations.

Repairing `misc` to a fixed two-bit field would change established numeric outputs. Without measured machine responses that would be an invented format. The tool therefore keeps the current mapping and supplies model-independent numeric bit experiments.

### Exact conversion sequence

1. Join the fields in the order above (no bit-string reversal).
2. If the integer value is < 1000, left-pad to 16 bits and prepend `1`; otherwise left-pad to 17 bits with `0`.
3. If the 17-bit string begins `00` and ends `0`, remove exactly one final zero bit and remember to prepend a decimal zero later. At most one bit is removed.
4. Convert the remaining bits to an unsigned decimal integer, apply the optional leading zero, then normalize to exactly five decimal characters.
5. Compute the UPC-style modulo-10 check digit (weights from the right: 3,1,3,1,3) and append it.

Trace for `--temperature 3 --size 0 --charge 0 --volume 2 --flow-rate 1 --purge 0 --misc 0`:

| Stage | Value |
| --- | --- |
| Raw fields | `11 0 00 0010 001 00` + empty suffix |
| Raw bits | `11000001000100` |
| 17-bit padded | `00011000001000100` |
| Trimmed | `0001100000100010` |
| Decimal integer | `6178` |
| Decimal payload | `06178` |
| Checksum | `0` |
| Complete code | **`061780`** |

Under the field model this nominally corresponds to 93 °C / 70 ml / 40 % flow. Public inventories associate the code with multiple espresso products, frequently listed as 60 ml.

### Coverage and collisions

Exhaustive enumeration of the seven-field domain:

- 49 152 combinations (`4×2×4×16×8×4×3`)
- 29 172 distinct valid six-digit outputs after five-digit-payload normalization
- Some codes have multiple inputs; `655378` is one explicit collision
- Published `674478` (payload `67447`) is outside the current field model and can only be rendered or mutated directly

This is a software mapping of the chosen option set, not evidence that firmware accepts every generated code or implements the same field semantics.

## Optical rendering

Custom implementation; not a standard Interleaved or Industrial 2-of-5 library. Digit patterns match the bar-only Industrial/Standard 2-of-5 data patterns, but the run-in `000` differs from the commonly documented Industrial start marker `110`. Standard-symbology compliance is therefore not claimed.

| Digit | Wide-bar pattern | Digit | Pattern |
| --- | --- | --- | --- |
| 0 | `00110` | 5 | `10100` |
| 1 | `10001` | 6 | `01100` |
| 2 | `01001` | 7 | `00011` |
| 3 | `11000` | 8 | `10010` |
| 4 | `00101` | 9 | `01010` |

- Run-in/start: `000`; run-out/stop: `101`
- Nominal advances: thin 4 px / wide 8 px + 4 px inter-bar space
- Actual black pixel widths: 5 px / 9 px (inclusive Pillow rectangles). White gap: 3 px. Geometry is intentional.
- Monochrome PNG, 50 px high; 10 px left margin, dynamic right quiet zone. Six digits → 36 bars, 364×50 px (14 wide bars).
- Quiet-zone ratio, printer scaling, orientation and scanner compatibility have not been established by successful physical test. Non-integer scaling can alter widths and acceptance.

Rendering of the original 200×50 pixel region is bit-identical; only the missing continuation and trailing quiet zone are added. A correctly checksummed PNG does not guarantee that any particular machine will accept the scan.

## Regressions and validation

```sh
python t-disk-barcode.py --self-test
```

Covers checksum vectors `061780`, `032711`, `032872`, `033510`, `297615`, `674478`; five field-derived codes; intermediate bits for `061780`; malformed-input rejection; high-bit and low-two-bit mutations; range overflow; randomized CSV generation and overwrite refusal; bar geometry and late-image pixels; exhaustive 49 152-input ambiguity audit.

`032711` is mathematically valid and reproducible from the field model. Product-label associations are not unique (multiple products can share a numeric code).

## Evidence and references

1. **Primary patent (nominal parameter fields, Table 3):** [US7231869B2](https://patents.google.com/patent/US7231869B2/en). Defines a 13-bit example, mentions error-checking bits and a 16-bit code; does not validate the extra fields or padding rules used here.
2. **Published code inventory (source of the 34-code CSV):** [Markus Birth, TASSIMO Barcodes (2013)](https://blog.mbirth.uk/2013/09/08/tassimo-barcodes-de.html). Multiple products share codes; some payloads exceed 65 535. The page itself notes that alignment of patent data with barcodes is incomplete.
3. **Independent physical trials:** [Reverse Engineering Stack Exchange — T-Disk barcodes](https://reverseengineering.stackexchange.com/questions/3919/reverse-engineering-t-disk-barcodes-for-tassimo-coffee-makers). Reported behaviour conflicts with a simple patent-volume interpretation.
4. **Machine instrumentation notes (unverified bit-order claim):** [Stuart Dalby forum (2021)](https://www.stuartdalby.co.uk/forums/view.php?topicId=2450). Reports mains-neutral-referenced electronics and alternative bit arrangements; does not establish the byte order of this encoder.
5. **Industrial 2-of-5 reference:** [Seagull Scientific barcode guide](https://barcodeguide.seagullscientific.com/Content/Symbologies/Industrial_2_of_5.htm). Used only for digit pattern comparison; the optical generator is intentionally non-standard.
6. **Later optical format (out of scope):** [Reverse Engineering Stack Exchange — tap barcode](https://reverseengineering.stackexchange.com/questions/32947/reverse-engineering-of-the-tap-barcode-of-tassimo-t-discs). Do not conflate its optical format with the six-digit renderer.

**Epistemic boundary:** The custom run-in pattern, `size`, variable-width `misc`, escape and trim logic are encoding rules of this tool. Priority is reproducibility and explicitly testable hypotheses over inventing undocumented production semantics.
