#!/usr/bin/env python3
"""Experimental T-Disc code generator, barcode renderer, and bitfield laboratory.

Two independently useful operations:

* Render a known, six-digit, check-digit-valid T-Disc code (recommended when the
  code is known). This supports payloads above 65535.
* Derive a code from an *experimental* field interpretation. This reproduces
  the original script's unusual bit assembly/padding and warns when several
  different field selections resolve to the same six-digit output.
* Inspect the checksum-stripped numeric payload and change individual numeric
  bits WITHOUT the legacy parameter model. Generate randomized/repeated low-two-
  bit experiments and a measurement worksheet.

IMPORTANT: This program deliberately preserves the original, NON-STANDARD
one-pattern-per-digit bar drawing, narrow/wide ordering, start/stop patterns,
bar advances and pixel raster. It is NOT replaced by a barcode library and is
not a claim of conventional Interleaved 2-of-5 compliance.

Requires Python >= 3.9 and Pillow (pip install Pillow).
"""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
import sys
from typing import Dict, List, Mapping, Optional, Sequence, Tuple, Union

try:
    from PIL import Image, ImageDraw
except ImportError as exc:
    raise SystemExit("Pillow is required: python -m pip install Pillow") from exc


# KEEP these original digit sequences: two wide bars per five-bar digit.
# Do not substitute standard/interleaved barcode encoding here.
DIGIT_BARS: Tuple[Tuple[int, ...], ...] = (
    (0, 0, 1, 1, 0),
    (1, 0, 0, 0, 1),
    (0, 1, 0, 0, 1),
    (1, 1, 0, 0, 0),
    (0, 0, 1, 0, 1),
    (1, 0, 1, 0, 0),
    (0, 1, 1, 0, 0),
    (0, 0, 0, 1, 1),
    (1, 0, 0, 1, 0),
    (0, 1, 0, 1, 0),
)
RUN_IN = (0, 0, 0)
RUN_OUT = (1, 0, 1)

# These values intentionally match the original renderer's POSITION advance.
# Pillow's inclusive rectangle endpoints result in 5/9 black pixels (rather
# than 4/8), with a three-pixel white gap. Changing this would change the
# original optical raster; only the canvas clipping is fixed below.
THIN_ADVANCE = 4
WIDE_ADVANCE = 8
INTER_BAR_STEP = 4
QUIET_ZONE = 10
BAR_HEIGHT = 50

TEMPERATURE_LABELS = ("cold", "warm (temperature unspecified)", "83 C", "93 C")
SIZE_LABELS = ("standard", "large")                 # Unverified extra bit
CHARGE_LABELS = (
    "fast charge + soak", "fast charge without soak",
    "slow charge + soak", "slow charge without soak",
)
VOLUME_ML = (50, 60, 70, 80, 90, 100, 110, 130, 150, 170, 190, 210, 230, 250, 275, 300)
FLOW_PERCENT = (30, 40, 50, 60, 70, 80, 90, 100)
PURGE_LABELS = ("slow / short", "slow / long", "fast / short", "fast / long")
# Original experimental variable-width suffix. These are NOT four fixed
# 2-bit values and their product/brand meanings are unverified.
MISC_BITS = ("", "1", "11")


@dataclass(frozen=True)
class BrewSettings:
    temperature: int
    size: int
    charge: int
    volume: int
    flow_rate: int
    purge: int
    misc: int

    def validate(self) -> None:
        for name, value, count in (
            ("temperature", self.temperature, 4),
            ("size", self.size, 2),
            ("charge", self.charge, 4),
            ("volume", self.volume, 16),
            ("flow_rate", self.flow_rate, 8),
            ("purge", self.purge, 4),
            ("misc", self.misc, 3),
        ):
            if type(value) is not int or not 0 <= value < count:
                raise ValueError(f"{name} must be an integer in range 0..{count - 1}")

    def brief(self) -> str:
        return (
            f"temperature={self.temperature} size={self.size} charge={self.charge} "
            f"volume={self.volume} flow_rate={self.flow_rate} "
            f"purge={self.purge} misc={self.misc}"
        )


@dataclass(frozen=True)
class EncodingTrace:
    field_bits: str
    padded_bits: str
    trimmed_bits: str
    decimal_before_leading_zero: str
    original_payload: str
    payload: str
    check_digit: int
    code: str
    used_low_value_escape: bool
    removed_low_bit: bool


def _is_ascii_digits(value: str) -> bool:
    return bool(value) and value.isascii() and value.isdecimal()


def calculate_check_digit(payload: str) -> int:
    """UPC-style mod-10 digit, weighted from the RIGHT (3,1,3,1,...).

    For this format, the encoded payload must contain exactly five ASCII
    digits. Weighting from the right makes parity explicit rather than relying
    on the input to have a particular length.
    """
    if not _is_ascii_digits(payload) or len(payload) != 5:
        raise ValueError("checksum payload must contain exactly five ASCII digits")
    weighted_sum = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(payload))
    )
    return (-weighted_sum) % 10


def validate_code(code: str) -> str:
    """Validate an existing complete six-digit code, retaining leading zeros."""
    if not isinstance(code, str) or len(code) != 6 or not _is_ascii_digits(code):
        raise ValueError("T-Disc code must be exactly six ASCII decimal digits")
    expected = calculate_check_digit(code[:5])
    if int(code[5]) != expected:
        raise ValueError(
            f"invalid check digit in {code}: expected {expected} for payload {code[:5]}"
        )
    return code


def code_from_payload(value: int) -> str:
    """Construct a valid six-digit code from the 0..99999 numeric payload.

    The checksum is calculated on its *five digit decimal rendering*, including
    leading zeroes; it is NOT calculated on the binary value or the barcode.
    """
    if type(value) is not int or not 0 <= value <= 99999:
        raise ValueError("numeric payload must be an integer from 0 to 99999")
    payload = f"{value:05d}"
    return payload + str(calculate_check_digit(payload))


def numeric_payload(code: str) -> int:
    """Extract only the integer represented by the five pre-checksum digits."""
    return int(validate_code(code)[:5])


def modify_payload_bit(code: str, index: int) -> str:
    """Flip bit index in the numeric value (0 = LSB), then recompute check.

    This is arithmetic on the five-digit integer, not bit reversal, byte order,
    or a proven firmware field. The result MUST fit into five decimal digits.
    """
    if type(index) is not int or not 0 <= index <= 16:
        raise ValueError("bit index must be between 0 and 16 (LSB = 0)")
    return code_from_payload(numeric_payload(code) ^ (1 << index))


def replace_low2(code: str, state: int) -> str:
    """Set only numeric payload bits 1:0, maintaining every higher bit."""
    if type(state) is not int or not 0 <= state <= 3:
        raise ValueError("low-two-bit value must be in range 0..3")
    value = numeric_payload(code)
    return code_from_payload((value & ~3) | state)


def inspect_code(code: str) -> None:
    """Display numeric representations; no physical-field interpretation."""
    value = numeric_payload(code)
    width = max(16, value.bit_length())
    bits = f"{value:0{width}b}"
    print(f"Six-digit code:           {code}")
    print(f"Five-digit payload:       {code[:5]} (integer {value})")
    print(f"Check digit:              {code[5]} (validated)")
    print(f"Minimum payload bit size: {value.bit_length()}")
    print(f"MSB->LSB view ({width}):       {bits}")
    print(f"LSB->MSB view ({width}):       {bits[::-1]}")
    print(f"Zero-extended 17-bit view: {value:017b}")
    print(f"Numeric bits 1:0:         {value & 3:02b}")
    print("NOTICE: these are numeric bit views, not proven byte-order or brewing fields.")
    possible = reverse_index().get(code, ())
    print(f"Legacy-model input mappings: {len(possible)} (NOT a physical decode)")
    if possible:
        print(f"Example legacy mapping:   {possible[0].brief()}")


def create_low2_experiment(baseline: str, dest: Path, repeats: int = 3,
                           seed: int = 0) -> Path:
    """Four controlled bit variants and randomized, balanced measurement CSV.

    Leaves the experiment folder intact and refuses to overwrite it. Each block
    includes all four states once, in seeded randomized order, so changing tank
    temperature and repeated operations are less likely to confound bit effects.
    """
    validate_code(baseline)
    if type(repeats) is not int or not 1 <= repeats <= 100:
        raise ValueError("repeats must be in range 1..100")
    if type(seed) is not int:
        raise ValueError("seed must be an integer")
    dest.mkdir(parents=True, exist_ok=False)
    variants = {state: replace_low2(baseline, state) for state in range(4)}
    try:
        for state, code in variants.items():
            generate_barcode(code, dest / f"low2_{state:02b}_{code}.png")
        columns = [
            "sequence", "repeat", "state_bits", "code", "numeric_payload",
            "payload_binary_17bit", "image", "baseline_code", "changed_bit_indices",
            "machine_model", "machine_revision", "disc_type", "barcode_position",
            "print_scale_dpi", "ambient_water_temp_c", "accepted", "error_code",
            "beverage_mass_g", "brew_s", "soak_s", "purge_s", "outlet_temp_c",
            "notes",
        ]
        rng = random.Random(seed)
        manifest = dest / "trials.csv"
        with manifest.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            seq = 0
            for repeat in range(1, repeats + 1):
                states = list(range(4))
                rng.shuffle(states)
                for state in states:
                    seq += 1
                    code = variants[state]
                    difference = numeric_payload(baseline) ^ numeric_payload(code)
                    writer.writerow({
                        "sequence": seq, "repeat": repeat,
                        "state_bits": f"{state:02b}", "code": code,
                        "numeric_payload": code[:5],
                        "payload_binary_17bit": f"{numeric_payload(code):017b}",
                        "image": f"low2_{state:02b}_{code}.png",
                        "baseline_code": baseline,
                        "changed_bit_indices": ",".join(
                            str(i) for i in range(2) if difference & (1 << i)
                        ) or "none",
                    })
        return manifest
    except (OSError, ValueError) as exc:
        raise OSError(f"Experiment incomplete in {dest}; partial files retained: {exc}") from exc


def audit_codes(path: Path) -> Tuple[int, int, Tuple[int, int, int, int]]:
    """Audit a CSV with a 'code' column; count DISTINCT validated decimal codes.

    Duplicated products using the same code are counted once, to avoid turning
    repeated retail listings into spurious evidence. Only the five-digit
    numeric payload is examined; these are not verified firmware control bits.
    """
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "code" not in reader.fieldnames:
            raise ValueError("CSV must have a header named 'code'")
        observed = []
        for lineno, record in enumerate(reader, start=2):
            code = (record.get("code") or "").strip()
            try:
                validate_code(code)
            except ValueError as exc:
                raise ValueError(f"CSV line {lineno}: {exc}") from exc
            observed.append(code)
    if not observed:
        raise ValueError("CSV has no code rows")
    codes = set(observed)
    counts = tuple(sum(numeric_payload(code) % 4 == i for code in codes)
                   for i in range(4))
    print(f"Inventory rows: {len(observed)}, distinct validated codes: {len(codes)}")
    print("Low TWO bits of the numeric five-digit payload (distinct codes):")
    for i, count in enumerate(counts):
        print(f"  {i:02b}: {count:>3} ({100 * count / len(codes):.1f}%)")
    print(f"Values requiring bit 16: {sum(numeric_payload(c) >= 65536 for c in codes)}")
    print("NOTICE: observational convenience sample; no machine-function inference.")
    return len(observed), len(codes), counts


def encode_settings(settings: BrewSettings) -> EncodingTrace:
    """Apply the original experimental mapping, with correct six-digit output.

    No claim is made that all resulting codes yield these physical dispense
    parameters on any particular Tassimo firmware or T-Disc generation.
    """
    settings.validate()
    # These fields are concatenated in THIS order, MSB first within each field.
    # There is no bit reversal or byte reversal.
    raw = (
        f"{settings.temperature:02b}"
        f"{settings.size:01b}"
        f"{settings.charge:02b}"
        f"{settings.volume:04b}"
        f"{settings.flow_rate:03b}"
        f"{settings.purge:02b}"
        f"{MISC_BITS[settings.misc]}"
    )

    # Preserve the original, unverified legacy escape/padding heuristic:
    # values below 1000 are prefixed with bit 16, otherwise zero-padded to 17.
    low_value_escape = int(raw, 2) < 1000
    if low_value_escape:
        padded = "1" + raw.rjust(16, "0")
    else:
        padded = raw.rjust(17, "0")

    # Preserve the original optional leading decimal zero and *single* low-bit
    # removal. The original code's loop could trim at most one trailing zero
    # because its minimum bit length was 16.
    leading_decimal_zero = padded.startswith("00") and padded.endswith("0")
    removed_low_bit = leading_decimal_zero
    trimmed = padded[:-1] if removed_low_bit else padded

    decimal_value = str(int(trimmed, 2))
    original_payload = ("0" if leading_decimal_zero else "") + decimal_value

    # FIX: Without this some parameter sets output only FIVE total digits,
    # and the left-anchored checksum would have the wrong parity. Existing
    # six-digit code outputs remain unchanged; raw outputs that were too
    # short are explicitly normalised to five payload digits before checksum.
    payload = original_payload.zfill(5)
    if len(payload) != 5:
        raise ValueError(
            f"legacy parameter mapping produced {len(payload)} payload digits; "
            "render a known code with --code instead"
        )

    digit = calculate_check_digit(payload)
    code = payload + str(digit)
    return EncodingTrace(
        field_bits=raw,
        padded_bits=padded,
        trimmed_bits=trimmed,
        decimal_before_leading_zero=decimal_value,
        original_payload=original_payload,
        payload=payload,
        check_digit=digit,
        code=code,
        used_low_value_escape=low_value_escape,
        removed_low_bit=removed_low_bit,
    )


def bar_sequence(code: str) -> Tuple[int, ...]:
    """Return exactly the original run-in, per-digit bars, and run-out."""
    validate_code(code)
    return (
        RUN_IN
        + tuple(bar for character in code for bar in DIGIT_BARS[int(character)])
        + RUN_OUT
    )


def image_width(code: str) -> int:
    """Allocate room for every bar plus left/right quiet zones."""
    bars = bar_sequence(code)
    return 2 * QUIET_ZONE + sum(
        (WIDE_ADVANCE if thick else THIN_ADVANCE) + INTER_BAR_STEP
        for thick in bars
    )


def generate_barcode(code: str, img_path: Union[Path, str]) -> Path:
    """Render the existing unconventional optical pattern WITHOUT clipping.

    Preserve the original inclusive horizontal rectangle endpoints and bar
    advance; the new canvas width is the only horizontal raster change.
    """
    bars = bar_sequence(code)
    output_path = Path(img_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width = image_width(code)
    image = Image.new("1", (width, BAR_HEIGHT), color=1)
    draw = ImageDraw.Draw(image)
    x = QUIET_ZONE
    for thick in bars:
        bar_advance = WIDE_ADVANCE if thick else THIN_ADVANCE
        # NOTE: x + bar_advance is INCLUSIVE to preserve original pixel raster.
        draw.rectangle((x, 0, x + bar_advance, BAR_HEIGHT - 1), fill=0)
        x += bar_advance + INTER_BAR_STEP
    image.save(output_path, format="PNG")
    return output_path


@lru_cache(maxsize=1)
def reverse_index() -> Mapping[str, Tuple[BrewSettings, ...]]:
    """All 49,152 possible input selections, indexed by generated output.

    This is an ambiguity audit, not a physical barcode decoder. Since leading
    zeros and variable-length suffixes discard information, code->selection
    may have multiple plausible inputs.
    """
    hits: Dict[str, List[BrewSettings]] = defaultdict(list)
    for t, s, c, v, f, p, m in product(
        range(4), range(2), range(4), range(16), range(8), range(4), range(3)
    ):
        settings = BrewSettings(t, s, c, v, f, p, m)
        hits[encode_settings(settings).code].append(settings)
    return {key: tuple(values) for key, values in hits.items()}


def _choice(name: str, labels: Sequence[str]) -> int:
    print(f"\n{name}:")
    for index, label in enumerate(labels):
        print(f"  {index:2d}  {label}")
    while True:
        try:
            response = input(f"Select {name} [0..{len(labels) - 1}]: ").strip()
        except EOFError as exc:
            raise ValueError("interactive input ended; use --code or supply all seven options") from exc
        if response.isascii() and response.isdecimal() and int(response) < len(labels):
            return int(response)
        print("Invalid selection; enter a number from the table.")


def interactive_settings() -> BrewSettings:
    print("Experimental parameter mapping; physical machine response is not verified.")
    return BrewSettings(
        temperature=_choice("Temperature", TEMPERATURE_LABELS),
        size=_choice("T-Disc size (experimental)", SIZE_LABELS),
        charge=_choice("Pre-brewing", CHARGE_LABELS),
        volume=_choice("Volume (patent nominal ml)", [f"{value} ml" for value in VOLUME_ML]),
        flow_rate=_choice("Flow (patent nominal percent)", [f"{value}%" for value in FLOW_PERCENT]),
        purge=_choice("Purge", PURGE_LABELS),
        misc=_choice("Misc (experimental bits)", ('none / ""', '"1"', '"11"')),
    )


def _print_trace(trace: EncodingTrace) -> None:
    print(f"Raw field bits:             {trace.field_bits}")
    print(f"17-bit padded/escaped bits: {trace.padded_bits}")
    print(f"Trimmed bits:               {trace.trimmed_bits}")
    print(f"Decimal (no leading zero): {trace.decimal_before_leading_zero}")
    print(f"Legacy decimal payload:    {trace.original_payload}")
    print(f"Five-digit payload:        {trace.payload}")
    print(f"Check digit:               {trace.check_digit}")
    print(f"Full six-digit code:       {trace.code}")
    if trace.original_payload != trace.payload:
        print("NOTE: Added leading zero(s) to normalise a previously short output.")


def run_self_test() -> None:
    """Useful fast regression check without external test-framework packages."""
    import tempfile

    if not __debug__:
        raise RuntimeError("--self-test requires assertions; run Python without -O/-OO")

    known_codes = (
        "061780", "032711", "032872", "033510", "297615", "674478"
    )
    for code in known_codes:
        assert validate_code(code) == code
        assert len(bar_sequence(code)) == 36
        assert sum(bar_sequence(code)) == 14
        assert image_width(code) == 364

    # Field vectors from the original implementation, NOT physical claims.
    vectors = (
        (BrewSettings(3, 0, 0, 2, 1, 0, 0), "061780"),
        (BrewSettings(1, 1, 0, 12, 3, 2, 0), "032711"),
        (BrewSettings(1, 1, 0, 13, 3, 2, 0), "032872"),
        (BrewSettings(1, 1, 1, 1, 3, 2, 0), "033510"),
        (BrewSettings(3, 1, 1, 1, 0, 0, 1), "297615"),
    )
    for fields, code in vectors:
        assert encode_settings(fields).code == code, (fields, code)

    assert encode_settings(BrewSettings(3, 0, 0, 2, 1, 0, 0)).field_bits == "11000001000100"
    assert encode_settings(BrewSettings(3, 0, 0, 2, 1, 0, 0)).padded_bits == "00011000001000100"
    assert encode_settings(BrewSettings(3, 0, 0, 2, 1, 0, 0)).trimmed_bits == "0001100000100010"

    # Old five-digit outputs must now have six digits with a valid check.
    old_short = encode_settings(BrewSettings(0, 0, 0, 7, 6, 2, 2))
    assert len(old_short.original_payload) == 4
    assert len(old_short.code) == 6
    validate_code(old_short.code)

    # Invalid code and invalid fields must fail rather than silently render.
    for invalid in ("", "06178", "061781", "abcdef", "０６１７８０", "67447X"):
        try:
            validate_code(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"incorrectly accepted code {invalid!r}")
    try:
        encode_settings(BrewSettings(4, 0, 0, 0, 0, 0, 0))
    except ValueError:
        pass
    else:
        raise AssertionError("invalid field was accepted")

    assert code_from_payload(6178) == "061780"
    assert [replace_low2("061780", i) for i in range(4)] == [
        "061766", "061773", "061780", "061797"
    ]
    assert modify_payload_bit("061780", 0) == "061797"
    assert modify_payload_bit("061780", 16) == "717144"
    assert numeric_payload("674478") == 67447
    try:
        modify_payload_bit(code_from_payload(65535), 16)  # 131071 > 99999
    except ValueError:
        pass
    else:
        raise AssertionError("17-bit mutation exceeding five decimal digits was accepted")
    for invalid_payload in (-1, 100000, 1.0):
        try:
            code_from_payload(invalid_payload)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid payload accepted: {invalid_payload!r}")

    index = reverse_index()
    assert sum(len(matches) for matches in index.values()) == 49152
    assert len(index["655378"]) >= 2  # original variable-length suffix collision
    assert len(index["032711"]) >= 2  # after six-digit normalisation
    assert "674478" not in index      # renderable directly, not constructible via legacy fields

    with tempfile.TemporaryDirectory() as temporary:
        path = generate_barcode("061780", Path(temporary) / "barcode.png")
        with Image.open(path) as img:
            assert img.size == (364, BAR_HEIGHT)
            assert img.mode == "1"
            assert img.getpixel((0, 0)) != 0         # left quiet zone
            assert img.getpixel((10, 0)) == 0        # first bar
            assert img.getpixel((14, 0)) == 0        # inclusive narrow bar end
            assert img.getpixel((15, 0)) != 0        # first quiet gap
            assert img.getpixel((363, 0)) != 0       # right quiet zone
            # End of image is no longer clipped: some black pixels must be
            # present to the right of the old 200px canvas.
            assert any(img.getpixel((x, 0)) == 0 for x in range(200, 350))

    with tempfile.TemporaryDirectory() as temporary:
        experiment = Path(temporary) / "sweep"
        manifest = create_low2_experiment("061780", experiment, repeats=3, seed=42)
        with manifest.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 12
        assert len({row["code"] for row in rows}) == 4
        assert {row["state_bits"] for row in rows} == {"00", "01", "10", "11"}
        assert all({row["state_bits"] for row in rows[(r*4):((r+1)*4)]}
                   == {"00", "01", "10", "11"} for r in range(3))
        assert len(list(experiment.glob("*.png"))) == 4
        try:
            create_low2_experiment("061780", experiment)
        except FileExistsError:
            pass
        else:
            raise AssertionError("experiment folder overwrite not prevented")

    with tempfile.TemporaryDirectory() as temporary:
        sample = Path(temporary) / "codes.csv"
        sample.write_text("code\n061780\n061780\n032872\n033510\n", encoding="utf-8")
        assert audit_codes(sample) == (4, 3, (0, 0, 1, 2))

    print(f"Self-test PASS: {len(known_codes)} known codes, 5 field vectors, "
          f"49,152-input collision audit, bit mutations, randomized sweep, image raster and validation.")
    print(f"Generated output space: {len(index):,} distinct six-digit codes "
          f"for 49,152 parameter selections (not one-to-one).")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="T-Disc experimental parameter encoder and original custom-bar renderer"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--code", help="render a valid six-digit code (optional numeric bit mutation)")
    mode.add_argument("--inspect-code", metavar="CODE", help="inspect numeric payload bit views; no PNG")
    mode.add_argument("--sweep-low2", metavar="CODE", help="four numeric low-bit variants, PNGs + trial CSV")
    mode.add_argument("--audit-codes", type=Path, metavar="CSV", help="audit a code-column CSV and low-bit histogram (no PNG)")
    mutation = parser.add_mutually_exclusive_group()
    mutation.add_argument("--flip-bit", type=int, metavar="N", help="flip numeric payload bit N (0..16; LSB=0), requires --code")
    mutation.add_argument("--set-low2", type=int, choices=range(4), metavar="0..3", help="set low two NUMERIC payload bits; requires --code")
    parser.add_argument("--experiment-dir", type=Path, help="folder for --sweep-low2 (must not already exist)")
    parser.add_argument("--repeats", type=int, metavar="N", help="balanced trial blocks for --sweep-low2 (default 3)")
    parser.add_argument("--seed", type=int, metavar="N", help="deterministic trial order random seed (default 0)")
    parser.add_argument("--temperature", type=int, choices=range(4))
    parser.add_argument("--size", type=int, choices=range(2))
    parser.add_argument("--charge", type=int, choices=range(4))
    parser.add_argument("--volume", type=int, choices=range(16))
    parser.add_argument("--flow-rate", type=int, choices=range(8))
    parser.add_argument("--purge", type=int, choices=range(4))
    parser.add_argument("--misc", type=int, choices=range(3))
    parser.add_argument("--output", type=Path, help="PNG path; defaults to barcode_<code>.png")
    parser.add_argument(
        "--require-unique", action="store_true",
        help="fail if another experimental input selection produces the same code"
    )
    parser.add_argument("--trace", action="store_true", help="show all parameter-encoding stages")
    parser.add_argument("--self-test", action="store_true", help="run built-in regression tests")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    fields = ("temperature", "size", "charge", "volume", "flow_rate", "purge", "misc")
    supplied = [getattr(args, name) is not None for name in fields]
    specialized = any((args.code is not None, args.inspect_code is not None,
                       args.sweep_low2 is not None, args.audit_codes is not None))
    sweep_options = any((args.experiment_dir is not None, args.repeats is not None,
                         args.seed is not None))
    mutated = args.flip_bit is not None or args.set_low2 is not None

    if args.self_test:
        if any((specialized, sweep_options, mutated, args.output is not None,
                args.trace, args.require_unique, any(supplied))):
            parser.error("--self-test must be used alone")
        run_self_test()
        return 0

    if sweep_options and args.sweep_low2 is None:
        parser.error("--experiment-dir/--repeats/--seed require --sweep-low2")
    if mutated and args.code is None:
        parser.error("--flip-bit and --set-low2 require --code")
    if specialized and any(supplied):
        parser.error("numeric code operations cannot be combined with legacy parameter fields")
    if specialized and args.require_unique:
        parser.error("--require-unique is only for legacy parameter generation")
    if specialized and args.trace:
        parser.error("--trace is for legacy parameter generation; use --inspect-code for numeric payloads")

    if args.audit_codes is not None:
        if args.output is not None or mutated:
            parser.error("--audit-codes cannot be combined with --output or numeric mutations")
        try:
            audit_codes(args.audit_codes)
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        return 0

    if args.sweep_low2 is not None:
        if args.output is not None or mutated:
            parser.error("--sweep-low2 cannot be combined with --output or numeric bit mutation")
        try:
            code = validate_code(args.sweep_low2)
            dest = args.experiment_dir or Path.cwd() / f"experiment_{code}"
            manifest = create_low2_experiment(
                code, dest, repeats=args.repeats if args.repeats is not None else 3,
                seed=args.seed if args.seed is not None else 0
            )
        except (OSError, ValueError) as exc:
            parser.error(str(exc))
        print(f"Created {manifest.parent}: four PNGs + {manifest.name}")
        print("Changes affect NUMERIC payload bits 1:0 only; brewing function UNKNOWN.")
        return 0

    if args.inspect_code is not None:
        if args.output is not None or mutated:
            parser.error("--inspect-code does not generate PNGs or accept bit mutations")
        try:
            inspect_code(validate_code(args.inspect_code))
        except ValueError as exc:
            parser.error(str(exc))
        return 0

    if args.code is not None:
        try:
            original = validate_code(args.code)
            code = original
            if args.flip_bit is not None:
                code = modify_payload_bit(original, args.flip_bit)
            if args.set_low2 is not None:
                code = replace_low2(original, args.set_low2)
        except ValueError as exc:
            parser.error(str(exc))
        if mutated:
            print(f"Numeric payload mutation: {original} -> {code}")
            if code == original:
                print("  Requested low-two-bit state already matches baseline; no bits changed.")
            print(f"  Before: {numeric_payload(original):017b} (bits16..0)")
            print(f"  After:  {numeric_payload(code):017b} (bits16..0)")
            print("  Only numeric payload bit(s) changed; check digit recomputed.")
        else:
            print(f"Validated existing six-digit code: {code} (no brewing parameters inferred)")
    else:
        if any(supplied) and not all(supplied):
            missing = ", ".join(name for name, present in zip(fields, supplied) if not present)
            parser.error(f"supply all seven legacy parameter fields or none; missing: {missing}")
        try:
            settings = (
                BrewSettings(*(getattr(args, name) for name in fields))
                if all(supplied) else interactive_settings()
            )
            trace = encode_settings(settings)
        except ValueError as exc:
            parser.error(str(exc))
        code = trace.code
        print(f"Selected experimental fields: {settings.brief()}")
        if args.trace:
            _print_trace(trace)
        print(f"Generated legacy-model code: {code} (physical beverage settings UNVERIFIED)")
        print("NOTICE: field layout, variable-length misc and <1000 escape are hypotheses.",
              file=sys.stderr)
        candidates = reverse_index()[code]
        if len(candidates) > 1:
            example = next((s for s in candidates if s != settings), None)
            message = (
                f"AMBIGUOUS: {len(candidates)} input selections generate {code}. "
                f"Another selection: {example.brief() if example else 'see source'}"
            )
            if args.require_unique:
                print(message, file=sys.stderr)
                print("No image generated (--require-unique).", file=sys.stderr)
                return 2
            print("WARNING: " + message, file=sys.stderr)

    target = args.output if args.output is not None else Path.cwd() / f"barcode_{code}.png"
    try:
        result = generate_barcode(code, target)
    except (OSError, ValueError) as exc:
        print(f"ERROR: failed to render barcode: {exc}", file=sys.stderr)
        return 1
    print(f"Saved {result} ({image_width(code)} x {BAR_HEIGHT} pixels)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
