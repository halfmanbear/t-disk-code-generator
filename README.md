# T-Disc barcode generator and bitfield laboratory

**Status: experimental protocol research.** This utility renders six-digit Tassimo T-Disc-style decimal codes using the **exact custom optical bar pattern from the original project**, plus a complete (unclipped) PNG canvas. It can also preserve the project's original parameter-to-code algorithm, inspect numeric payload bits, produce controlled bit mutations, prepare repeatable experiments, and audit a dataset of observed codes.

**Do not confuse three different claims:**

1. **Validated arithmetic:** six decimal digits, of which the final digit is a UPC-style modulo-10 checksum of the previous five decimal digits.
2. **Preserved project implementation:** the unusual five-bar-per-digit renderer, the original field assembly, the variable-width `misc` suffix, and the `<1000` escape/trimming heuristic. Preservation does **not** verify the latter as Tassimo firmware behaviour.
3. **Unverified physical interpretation:** the actual brewing variables, meaning of `misc`/low-order bits, scanner tolerance and machine-specific handling. Known codes and correct checksums do not establish a reliable field decoder.

See [Evidence and references](#evidence-and-references) for patent data and independent experiments.

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

Requires six **ASCII** digits with a valid check digit. A known code is the preferred starting point because this pathway makes no assumptions about brewing fields. It accepts payload values beyond 65,535, unlike the legacy field generator. Default output: `barcode_<six_digit_code>.png` in the current directory. **Normal PNG rendering overwrites an existing filename.**

### Inspect the checksum-stripped numeric payload

```sh
python t-disk-barcode.py --inspect-code 061780
python t-disk-barcode.py --inspect-code 674478
```

Prints the five-digit decimal payload, numeric value, minimum bit length, a zero-extended 16/17-bit MSB-first view, an LSB-first *display*, two lowest numeric bits, and the number of **legacy-model** inputs producing the code. No image is written. Bit reversal in the display is **not** a claim that firmware uses a particular byte order; bit order, byte order, sign and field alignment are separate hypotheses.

### Alter a numeric payload bit without going through the legacy parameter model

```sh
python t-disk-barcode.py --code 061780 --flip-bit 0
python t-disk-barcode.py --code 061780 --flip-bit 16  # -> 717144
python t-disk-barcode.py --code 061780 --set-low2 0  # -> 061766
```

`--flip-bit N` toggles bit `N` in the **unsigned integer represented by the five pre-checksum decimal digits**, with bit zero the least significant bit; allowed indices are 0–16. `--set-low2 N` replaces bits 1:0 with `00`, `01`, `10` or `11` (CLI values 0–3), leaving all higher numeric bits identical. The decimal check digit is always recalculated. Mutations that would exceed the five-decimal-digit range 0–99,999 are rejected rather than truncated. **These are numeric mutations, not guaranteed independent firmware control changes.**

### Generate a balanced low-two-bit experiment

```sh
python t-disk-barcode.py --sweep-low2 061780 \
  --experiment-dir experiments/espresso_01 \
  --repeats 3 --seed 42
```

Generates four PNGs, one for each possible low-two-bit state, and a CSV measurement template `trials.csv`. There are three randomized **blocks**, each containing all four states exactly once, for 12 planned observations. A fixed seed makes the proposed test order reproducible. The output directory **must not exist**; the program refuses to overwrite earlier experiment data.

| State | Five-digit decimal payload | Complete check-digit-valid barcode |
| --- | --- | --- |
| `00` | `06176` | `061766` |
| `01` | `06177` | `061773` |
| `10` | `06178` | `061780` (baseline) |
| `11` | `06179` | `061797` |

All four values differ *only* in numeric bits 1:0 before recomputing the check digit. The CSV includes planned sequence/repeat, encoded state, code, numeric payload, changed bits, PNG filename, machine/revision, original disc and barcode placement, printer settings, scan acceptance/error, measured mass, phase timings, outlet temperature and notes. The measurement columns are empty until you populate them. Record the printed code and actual observed results rather than interpreting the bit values beforehand.

**Experimental controls:** use the same machine, disc geometry, barcode position, print size, orientation, supply and instrument setup. Repeat measurements; rotate/randomize test order to limit warm-up and carry-over effects. Measure mass and dispense phases rather than inferring controller volume from advertised product serving size. Control for soak/purge retention. Record physical results for a second baseline before assigning a general meaning to the low bits. Do not assume novel codes will be accepted or that an accepted code is safe to run unattended; test with suitable containment and supervision. Do not connect a grounded computer or logic analyser directly to potentially mains-referenced machine electronics without an appropriate isolation design.

### Audit a code inventory

```sh
python t-disk-barcode.py --audit-codes published_codes_2013.csv
```

The input must be a UTF-8 CSV with a `code` column containing complete six-digit codes. The utility validates checksums, counts **distinct codes** (product listings can share codes), and reports the numeric two-bit histogram and count of payloads using bit 16. Invalid or empty data fails rather than silently skewing results.

The included `published_codes_2013.csv` is a reproducible **34-distinct-code historical convenience sample** transcribed from Markus Birth's September 2013 public TASSIMO barcode list, excluding its separate *Professional* category. Its observed histogram is:

| Numeric bits 1:0 | Number of distinct codes |
| --- | ---: |
| `00` | **0** |
| `01` | 11 |
| `10` | 5 |
| `11` | 18 |

Nine of the 34 payload integers require bit 16. **Interpretation:** the absence of `00` in this non-random historical selection makes a reserved/invalid state worth testing, **not** a proven property of the protocol. Do not infer a product brand, hot/cold operation, or extension version from those two bits without physical measurements. A different cohort or machine generation might have different distributions.

### Legacy interactive or explicit field generation

```sh
python t-disk-barcode.py
python t-disk-barcode.py \
  --temperature 3 --size 0 --charge 0 \
  --volume 2 --flow-rate 1 --purge 0 --misc 0 --trace
```

The explicit example produces `061780`; this is a **software regression vector**, **not** a verified 70 ml recipe for espresso. If parameter inputs collide, the script prints an alternative selection. `--require-unique` refuses to generate a code with other inputs in the *same legacy mapping* (exit status 2); this does **not** mean that a unique mapping is physically correct. All seven fields must be supplied together or none (interactive prompts).

```sh
python t-disk-barcode.py \
  --temperature 0 --size 0 --charge 0 \
  --volume 0 --flow-rate 0 --purge 0 --misc 1 --require-unique
```

This rejects the colliding code `655378`: the same code also comes from `purge=1, misc=0`, all other choices held equal.

Run `python t-disk-barcode.py --help` for the complete switch set. Specialized numeric modes, experimental field generation and the self-test are mutually exclusive.

## Known versus hypothesized bitfields

### Patent-defined **nominal** 13-bit fields

US7231869B2 Table 3 describes fields in this order: temperature (2), cartridge charge (2), volume (4), flow (3), purge (2). It describes an **example** of how operational variables can be represented, **not** a verified bit-level interpretation of every deployed decimal barcode. It also mentions extra data bits for error checking and a 16-bit code example. The patent's position numbering does not establish how to align its bits with the five-digit integer of any product.

| Parameter | Values by input index 0, 1, 2, ... | Status |
| --- | --- | --- |
| Temperature, 2 bits | `00` cold; `01` warm (no stated numeric value); `10` 83°C; `11` 93°C | Patent nominal |
| Charge, 2 bits | `00` fast+soak; `01` fast/no soak; `10` slow+soak; `11` slow/no soak | Patent nominal |
| Volume, 4 bits | see table below | Patent nominal; disputed experimentally |
| Flow, 3 bits | `000` 30%, `001` 40%, `010` 50%, `011` 60%, `100` 70%, `101` 80%, `110` 90%, `111` 100% | Patent nominal |
| Purge, 2 bits | `00` slow/short; `01` slow/long; `10` fast/short; `11` fast/long | Patent nominal |

| Volume index | Bits | Patent ml | Volume index | Bits | Patent ml |
| ---: | --- | ---: | ---: | --- | ---: |
| 0 | `0000` | 50 | 8 | `1000` | 150 |
| 1 | `0001` | 60 | 9 | `1001` | 170 |
| 2 | `0010` | 70 | 10 | `1010` | 190 |
| 3 | `0011` | 80 | 11 | `1011` | 210 |
| 4 | `0100` | 90 | 12 | `1100` | 230 |
| 5 | `0101` | 100 | 13 | `1101` | 250 |
| 6 | `0110` | 110 | 14 | `1110` | 275 |
| 7 | `0111` | 130 | 15 | `1111` | 300 |

A published physical reverse-engineering effort found behaviours that did not consistently fit this simple four-bit volume table. Do not assume the values above are measured target volumes or that temperature is fixed at the patent's nominal values on your machine.

### Original-script extras: `size`, `misc`, escape and trim

The original Python code concatenates **MSB-first**:

```text
temperature(2) | size(1) | charge(2) | volume(4) | flow(3) | purge(2) | misc(0..2)
```

- `size`: **one bit**, 0 = regular / 1 = large according to the project. Location/meaning **unverified** against the patent.
- `misc`: **not currently a fixed-width field**. Input `0` appends `""` (zero bits), input `1` appends `"1"` (one bit), input `2` appends `"11"` (two bits). A fourth state does **not** exist in this legacy interface.
- The original README's `misc=00` padding, `01` reserved, `10` Costa and `11` Starbucks/Maxwell statements were **not supported** by the original Python code or the patent. The suggestion that numeric bits 1:0 might form a fixed three-of-four-state control remains **an experiment to perform**, not a replacement mapping. Even if a fixed trailer exists, `misc` need not be that trailer.
- The `<1000` high-bit escape and optional bit removal are **legacy heuristics**, with no established firmware explanation. They can change alignment, collapse distinct input combinations and prevent the mapping from reaching many real-world payloads.

**Why not just repair `misc` into two bits?** That would eliminate some encoding ambiguity but change established numeric outputs. Without a set of physically measured machine responses, it would be an invented format. This tool preserves compatibility and provides model-independent numeric bit experiments instead.

### Exact legacy conversion (retained for compatibility)

1. Join fields in the order above. **Do not reverse the resulting string**, notwithstanding the original README's incorrect step.
2. If the integer value of those bits is **less than 1000 decimal**, left-pad to 16 bits and prepend `1`; otherwise left-pad to 17 bits with `0`.
3. If that 17-bit string begins `00` **and** ends `0`, remove exactly one final zero bit and remember to prepend a zero character to the decimal text. Otherwise leave bits unchanged. The original loop could remove at most one bit due to its minimum length condition.
4. Convert the remaining bits into an unsigned decimal integer, prepend the optional decimal zero, then normalize the decimal string to **exactly five characters**. This last normalization was added to avoid erroneous five-character *complete* barcodes.
5. Compute the UPC-style modulo-10 digit on five decimal characters (weights from right `3,1,3,1,3`), append it and render all six decimal digits.

Reproducible trace for `--temperature 3 --size 0 --charge 0 --volume 2 --flow-rate 1 --purge 0 --misc 0`:

| Stage | Value |
| --- | --- |
| Raw fields | `11 0 00 0010 001 00` + empty suffix |
| Raw bits | `11000001000100` |
| 17-bit padded bits | `00011000001000100` |
| Trimmed bits | `0001100000100010` |
| Decimal integer | `6178` |
| Decimal payload | `06178` |
| Checksum | `0` |
| Complete code | **`061780`** |

The fields nominally imply `temperature=93°C`, `volume=70ml`, `flow=40%` under the original model, **not an assertion about the product sold with `061780`**. Public inventories associate that code with multiple espresso products, often described as 60 ml.

### Coverage and collisions

Exhaustive self-test of the project's seven-field input domain:

- **49,152** combinations (`4×2×4×16×8×4×3`).
- **29,172** distinct valid six-digit decimal outputs after the corrected five-digit-payload normalization.
- Some codes have multiple legacy inputs; `655378` is one explicit collision.
- Published `674478` has five-digit payload `67447` (a 17-bit integer) and is **not produced** by the current legacy model; it can be rendered or mutated directly.

This is a **software mapping** of user options, not evidence that firmware accepts all resulting codes or supports those field semantics.

## Deliberately preserved optical rendering

This is the project's custom implementation and is **not** replaced by a standard Interleaved 2-of-5 or Industrial 2-of-5 library. The digit patterns match the Industrial/Standard 2-of-5 *bar-only* data patterns, but the project's run-in `000` differs from a commonly documented Industrial 2-of-5 start marker `110`. It is therefore inappropriate to assert standard symbology compliance.

| Digit | Wide-bar pattern (`1` = wide) | Digit | Pattern |
| --- | --- | --- | --- |
| 0 | `00110` | 5 | `10100` |
| 1 | `10001` | 6 | `01100` |
| 2 | `01001` | 7 | `00011` |
| 3 | `11000` | 8 | `10010` |
| 4 | `00101` | 9 | `01010` |

- Original run-in/start bars: `000`; run-out/stop bars: `101`.
- Bar advances: thin 4 px / wide 8 px, followed by a 4 px advance for spacing.
- **Actual black pixel widths are 5 px / 9 px** because the original Pillow rectangle used inclusive endpoints. White gap between consecutive bars is 3 px. These pixels are intentionally preserved, not silently corrected.
- Monochrome PNG: 50 px high; 10 px start margin, dynamic complete right margin. For six digits: 3 start + 30 data + 3 end = **36 bars** and **364×50 px** (14 wide bars). The original 200px canvas truncated the barcode.
- Narrow/quiet-zone ratio, printer scaling, orientation and scanner compatibility have **not** been established by a successful physical test in this project. Printing at a non-integer scale may alter widths and scan behaviour.

**Rendering invariance:** existing 200×50 pixels of the original rendering are retained exactly; only the missing continuation and trailing quiet zone are added. Tests exercise the new width and original bar geometry. A rendered PNG with correct checksum is not proof a given machine will scan it.

## Regressions and validation

```sh
python t-disk-barcode.py --self-test
```

Covers known checksum vectors `061780`, `032711`, `032872`, `033510`, `297615`, `674478`; five original parameter-derived code vectors; intermediate bits for `061780`; validation and malformed input rejection; high-bit and low-two-bit numeric mutations; range overflow; randomized/balanced CSV creation and overwrite refusal; bar width and late-image pixels; and the exhaustive 49,152-input ambiguity audit.

`032711` is mathematically valid and reproducible with original parameters, **but its earlier README association with Twinings Earl Grey is not corroborated**. The cited published list gives `033510` for Earl Grey and `032872` for English Breakfast. Product labels can share numeric codes, so labels are not a unique reverse decode.

## Evidence and references

1. **Primary patent (nominal parameter fields, Table 3):** [US7231869B2, *Machine for the preparation of beverages*](https://patents.google.com/patent/US7231869B2/en). Defines a 13-bit *example*, mentions additional error-checking bits and 16-bit code; does not validate the original project's appended fields or legacy padding.
2. **Historical published code inventory (source for included 34-code CSV):** [Markus Birth, *TASSIMO Barcodes* (2013)](https://blog.mbirth.uk/2013/09/08/tassimo-barcodes-de.html). Multiple products share six-digit codes; some payloads exceed 65,535. The page itself states that aligning patent data with barcode codes is not fully established.
3. **Independent physical trials and alternative bitfield hypotheses:** [Reverse Engineering Stack Exchange — reverse engineering T-Disk barcodes](https://reverseengineering.stackexchange.com/questions/3919/reverse-engineering-t-disk-barcodes-for-tassimo-coffee-makers). Reported outputs conflict with a simple patent-volume interpretation.
4. **Independent machine instrumentation and little-endian hypothesis (unverified):** [Stuart Dalby forum discussion (2021)](https://www.stuartdalby.co.uk/forums/view.php?topicId=2450). Reports electrically hazardous mains-neutral-referenced controller electronics and claims alternative bit arrangements fit some observations better. This does **not** establish the byte order of this project's encoder.
5. **Industrial 2-of-5 reference:** [Seagull Scientific barcode guide](https://barcodeguide.seagullscientific.com/Content/Symbologies/Industrial_2_of_5.htm) for bar-only two-of-five digit structure and quiet-zone principles. The user-supplied optical generator is intentionally preserved rather than standardized.
6. **Separate newer style, out of scope:** [Reverse Engineering Stack Exchange — tap barcode](https://reverseengineering.stackexchange.com/questions/32947/reverse-engineering-of-the-tap-barcode-of-tassimo-t-discs). Do not conflate its optical format with the six-digit renderer.

**Attribution and epistemic boundary:** `t-disk-barcode.py` originally supplied by the project owner; its custom run-in pattern, `size`, variable-width `misc`, escape and trim logic are not claimed to originate from the patent. This version prioritizes reproducibility and explicitly testable hypotheses over inventing undocumented production semantics.
