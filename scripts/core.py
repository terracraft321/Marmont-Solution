"""Deterministic text reproduction and independent consistency checks.

The final transcription, proposed key and editorial decisions are inputs.
Successful checks establish internal reproducibility, not a unique historical
decipherment. No model service, corpus download or network access is used.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path, PurePosixPath
import re
import tempfile
import unicodedata
from urllib.parse import unquote, urlsplit


UNRESOLVED = "⟦UNRESOLVED:TARGET⟧"
TEXT_OUTPUTS = (
    "solution/literal.txt",
    "solution/reading.md",
    "solution/reading_alignment.tsv",
)
PLATE_SIZE = (1051, 1246)
OPEN_ALTERNATIVES = {
    "TARGET": {"SAMAJESTE", "LEMPEREUR", "ELLE"},
    "FOUR_DOTS": {"DE", "DANS"},
    "RHO": {"", "PAR"},
    "LOW_INWARD_ARCH": {"S", ""},
    "ARCH_COMPOUND": {"", "ET"},
    "SLOOP": {"DES", "LES"},
}


class ValidationError(ValueError):
    """A failed integrity or consistency check."""


def require(condition: bool, message: str) -> None:
    """A check that remains active with Python's -O option."""
    if not condition:
        raise ValidationError(message)


def read_tsv(path: Path, required: tuple[str, ...] = ()) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames
        require(bool(fields), f"Empty TSV: {path.name}")
        require(len(fields) == len(set(fields)), f"Duplicate TSV column: {path.name}")
        require(set(required) <= set(fields), f"Missing required TSV columns: {path.name}")
        records = list(reader)
    for number, record in enumerate(records, 2):
        require(None not in record and all(value is not None for value in record.values()),
                f"Malformed TSV record: {path.name}:{number}")
    return records


def integer(value: str | int, description: str) -> int:
    require(not isinstance(value, bool), f"Invalid integer: {description}")
    try:
        result = int(value)
    except (ValueError, TypeError) as exc:
        raise ValidationError(f"Invalid integer: {description}") from exc
    require(str(result) == str(value), f"Noncanonical integer: {description}")
    return result


def normalize(text: str) -> str:
    """Coordinate alphabet: NFD, uppercase A-Z, and one ¤ for TARGET.

    Accents, spaces, brackets and punctuation do not occupy coordinates.
    The visible unresolved marker occupies one coordinate, never 19 letters.
    """
    text = text.replace(UNRESOLVED, "¤")
    return "".join(char for char in unicodedata.normalize("NFD", text).upper()
                   if "A" <= char <= "Z" or char == "¤")


def load(root: Path) -> dict:
    root = Path(root)
    folder = root / "inputs"
    key_rows = read_tsv(folder / "key.tsv", ("label", "value", "occurrences"))
    key: dict[str, str] = {}
    for record in key_rows:
        label = record["label"]
        require(bool(label) and not any(char.isspace() for char in label),
                "Key labels must be nonempty tokens")
        require(label not in key, f"Duplicate key label: {label}")
        key[label] = record["value"]
    lines = (folder / "transcription.txt").read_text(encoding="utf-8").splitlines()
    require(all(line.strip() for line in lines), "Transcription contains an empty row")
    rows = [line.split() for line in lines]
    readings = json.loads((folder / "reading_rows.json").read_text(encoding="utf-8"))
    reading = json.loads((folder / "reading.json").read_text(encoding="utf-8"))
    units = read_tsv(folder / "units.tsv", (
        "row", "token", "label", "value", "evidence_class",
        "left", "top", "right", "bottom",
    ))
    changes = read_tsv(folder / "editorial_interventions.tsv", (
        "row", "operation", "candidate_start_1based", "candidate_end_exclusive_1based",
        "reading_start_1based", "reading_end_exclusive_1based", "candidate", "reading", "reason",
    ))
    uncertainties = read_tsv(folder / "uncertainties.tsv", (
        "label", "value", "occurrences", "alternatives", "status", "note",
    ))
    return {"key_rows": key_rows, "key": key, "rows": rows, "readings": readings,
            "reading": reading, "units": units, "changes": changes,
            "uncertainties": uncertainties}


def render(rows: list[list[str]], key: dict[str, str]) -> str:
    """Direct left-to-right key lookup, preserving the 24 manuscript rows."""
    rendered: list[str] = []
    for row in rows:
        values: list[str] = []
        for label in row:
            require(label in key, f"Missing key value: {label}")
            values.append(key[label])
        rendered.append("".join(values))
    return "\n".join(rendered) + "\n"


def _supporting_checks(root: Path, data: dict) -> dict:
    """Check the current defect apparatus and published-comparison addresses."""
    folder = Path(root) / "inputs"
    key, rows = data["key"], data["rows"]
    unit_index = {f"r{int(unit['row']):02d}_t{int(unit['token']):02d}": unit for unit in data["units"]}

    def valid_box(box: list, description: str) -> tuple[int, int, int, int]:
        require(isinstance(box, list) and len(box) == 4, f"Malformed bounding box: {description}")
        left, top, right, bottom = (integer(value, description) for value in box)
        require(0 <= left < right <= PLATE_SIZE[0] and 0 <= top < bottom <= PLATE_SIZE[1],
                f"Bounding box outside the source plate: {description}")
        return left, top, right, bottom

    defects = json.loads((folder / "defects.json").read_text(encoding="utf-8"))
    require(defects["source_size_px"] == list(PLATE_SIZE), "Defect plate dimensions differ")
    sites = defects["sites"]
    require(isinstance(sites, list) and len(sites) == 17, "Expected 17 defect and gap sites")
    ids: set[str] = set()
    c_addresses: set[str] = set()
    counts = Counter()
    for site in sites:
        name = site["id"]
        require(name not in ids, f"Duplicate defect ID: {name}")
        ids.add(name)
        row = integer(site["row"], "defect row")
        require(1 <= row <= 24, f"Invalid defect row: {name}")
        first, last = (integer(value, "defect token span") for value in site["token_span_1based_inclusive"])
        require(1 <= first <= last <= len(rows[row - 1]), f"Invalid defect token span: {name}")
        expected_units = [f"r{row:02d}_t{token:02d}" for token in range(first, last + 1)]
        require(site["source_units"] == expected_units, f"Defect addresses disagree with its span: {name}")
        labels = rows[row - 1][first - 1:last]
        require(site["current_labels"] == labels, f"Defect labels differ from transcription: {name}")
        require(site["literal_values"] == [key[label] for label in labels], f"Defect key values differ: {name}")
        context_first, context_last = (integer(value, "defect context span")
                                       for value in site["context_token_span_1based_inclusive"])
        require(1 <= context_first <= first <= last <= context_last <= len(rows[row - 1]),
                f"Defect context does not contain its tokens: {name}")
        left, top, right, bottom = valid_box(site["bbox_ltrb"], name)
        for address in expected_units:
            unit = unit_index[address]
            require(left <= int(unit["left"]) < int(unit["right"]) <= right
                    and top <= int(unit["top"]) < int(unit["bottom"]) <= bottom,
                    f"Defect source rectangle does not contain its unit: {name}, {address}")
        if "adjacent_row_bbox_ltrb" in site:
            valid_box(site["adjacent_row_bbox_ltrb"], name + " adjacent row")
            require(1 <= integer(site["adjacent_row"], "adjacent row") <= 24,
                    f"Invalid adjacent defect row: {name}")
        require(site["origin_assessment"] == "UNDECIDABLE", f"Defect origin must remain qualified: {name}")
        kind = site["kind"]
        require(kind in {"existing_unit", "gap"}, f"Unknown defect kind: {name}")
        counts[kind] += 1
        if kind == "existing_unit":
            require(integer(site["existing_cipher_units_at_site"], "defect unit count") == len(expected_units),
                    f"Wrong existing-unit count at defect: {name}")
            require(not c_addresses.intersection(expected_units), f"Duplicated class-C defect unit: {name}")
            c_addresses.update(expected_units)
        else:
            require(integer(site["existing_cipher_units_at_site"], "gap unit count") == 0,
                    f"A gap cannot add existing cipher units: {name}")
            require(all(address in unit_index for address in site["gap_between_units"]),
                    f"Gap references a nonexistent neighboring unit: {name}")
        for value, comparison_labels in site["comparison_labels_by_letter"].items():
            expected = sorted(label for label, mapped in key.items() if not label.startswith("@") and mapped == value)
            require(comparison_labels == expected, f"Defect comparison label set differs from key: {name}, {value}")
    expected_c = {address for address, unit in unit_index.items() if unit["evidence_class"] == "C"}
    require(c_addresses == expected_c and len(c_addresses) == 14, "Defect sites do not exactly cover class C")
    require(dict(counts) == {"existing_unit": 13, "gap": 4}, "Wrong existing-site / gap counts")
    require(defects["counts"] == {"sites": 17, "existing_unit_sites": 13, "existing_cipher_units": 14, "gap_sites": 4},
            "Defect count summary differs from its sites")

    comparison = read_tsv(folder / "published_key_comparison.tsv", (
        "label", "proposed_value", "published_letter_value", "occurrences", "source_units", "source_id", "evidence_limit",
    ))
    require(len(comparison) == 33, "Expected 33 reported published-key label comparisons")
    seen: set[str] = set()
    matched_units = 0
    for record in comparison:
        label = record["label"]
        require(label in key and label not in seen, f"Invalid or duplicate published-key label: {label}")
        seen.add(label)
        require(record["proposed_value"] == record["published_letter_value"] == key[label],
                f"Published-key comparison value mismatch: {label}")
        addresses = record["source_units"].split(";")
        expected = [address for address, unit in unit_index.items() if unit["label"] == label]
        require(len(addresses) == len(set(addresses)) and set(addresses) == set(expected),
                f"Published-key comparison address set differs: {label}")
        require(integer(record["occurrences"], "published-key occurrences") == len(expected),
                f"Published-key occurrence count differs: {label}")
        require(bool(record["source_id"]) and bool(record["evidence_limit"].strip()),
                f"Missing published-key source qualification: {label}")
        matched_units += len(expected)
    require(matched_units == 435, "Expected 435 units in the reported published-key comparison")

    history = read_tsv(folder / "historical_comparison.tsv", (
        "entity", "order_central_sequence_position", "letter_sequence_position", "letter_rows",
        "comparison_result", "source_id", "source_citation", "comparison_limit",
    ))
    require(len(history) == 10, "Expected 10 historical-comparison rows")
    sequence: list[int] = []
    categories = Counter()
    for record in history:
        require(all(record[name].strip() for name in ("entity", "source_id", "source_citation", "comparison_limit")),
                "Incomplete historical source or qualification")
        for part in record["letter_rows"].split(";"):
            endpoints = [integer(value, "historical row reference") for value in re.split("[–-]", part)]
            require(len(endpoints) in {1, 2} and 1 <= endpoints[0] <= endpoints[-1] <= 24,
                    "Historical comparison cites a nonexistent row")
        if record["order_central_sequence_position"]:
            position = integer(record["order_central_sequence_position"], "historical order position")
            require(integer(record["letter_sequence_position"], "letter sequence position") == position,
                    "Reported central force sequence does not match")
            sequence.append(position)
        categories[record["comparison_result"]] += 1
    require(sorted(sequence) == list(range(1, 8)), "Historical central sequence must cover positions 1–7")
    require(dict(categories) == {"different_detail_or_quantity": 2, "substantive_correspondence": 7, "letter_only": 1},
            "Historical comparison category counts differ")
    return {"defect_sites": 17, "class_C_units_covered": 14, "gap_sites": 4,
            "reported_partial_key_labels": 33, "reported_partial_key_units": 435,
            "historical_comparison_rows": 10, "central_sequence_positions": 7}


def validate(root: Path) -> tuple[dict, dict]:
    data = load(root)
    rows, key = data["rows"], data["key"]
    frequencies = Counter(label for row in rows for label in row)
    cipher = {label: count for label, count in frequencies.items() if not label.startswith("@")}
    require(len(rows) == 24, "Expected 24 transcription rows")
    require(sum(frequencies.values()) == 1310, "Expected 1,310 total units")
    require(sum(cipher.values()) == 1300, "Expected 1,300 cipher units")
    require(len(cipher) == 155 and len(frequencies) == 163, "Wrong cipher or cleartext label inventory")
    require(sum(count == 1 for count in cipher.values()) == 50, "Wrong singleton label count")
    require(set(frequencies) == set(key), "Key coverage differs from the transcription")
    for record in data["key_rows"]:
        require(integer(record["occurrences"], "key occurrences") == frequencies[record["label"]],
                f"Key frequency differs for {record['label']}")
    require(key["TARGET"] == UNRESOLVED, "TARGET must retain its explicit unresolved marker")
    literal = render(rows, key)
    require(key["q"] == "T" and "HOMMET" in literal, "Literal q=T / HOMMET must remain unrepaired")
    data["literal"] = literal
    literal_rows = literal.splitlines()

    addresses: set[tuple[int, int]] = set()
    classes: Counter = Counter()
    contextual_labels: set[str] = set()
    clear: list[tuple[tuple[int, int], str]] = []
    for record in data["units"]:
        row = integer(record["row"], "unit row")
        token = integer(record["token"], "unit token")
        address = (row, token)
        require(1 <= row <= len(rows) and 1 <= token <= len(rows[row - 1]),
                f"Unit address out of range: r{row}:t{token}")
        require(address not in addresses, f"Duplicate unit address: r{row}:t{token}")
        addresses.add(address)
        label = record["label"]
        require(rows[row - 1][token - 1] == label, f"Unit label mismatch: r{row}:t{token}")
        require(record["value"] == key[label], f"Unit value mismatch: r{row}:t{token}")
        category = record["evidence_class"]
        require(category in {"A", "B", "C", "cleartext"}, f"Unknown unit evidence class: {category}")
        require((category == "cleartext") == label.startswith("@"),
                f"Cipher / cleartext misclassification: r{row}:t{token}")
        classes[category] += 1
        if category == "B":
            contextual_labels.add(label)
        if category == "cleartext":
            require(label == "@" + record["value"], f"Invalid cleartext label: {label}")
            clear.append((address, record["value"]))
        left, top, right, bottom = (integer(record[name], f"unit {name}")
                                    for name in ("left", "top", "right", "bottom"))
        require(0 <= left < right <= PLATE_SIZE[0] and 0 <= top < bottom <= PLATE_SIZE[1],
                f"Crop coordinates outside source plate: r{row}:t{token}")
    require(len(addresses) == 1310, "Incomplete unit-coordinate ledger")
    require(dict(classes) == {"A": 1232, "B": 54, "C": 14, "cleartext": 10},
            "Unexpected evidence-class counts")
    clear.sort()
    require([address for address, _ in clear] == [(14, token) for token in range(41, 51)],
            "Visible cleartext positions differ")
    require("".join(value for _, value in clear) == "CONSEQUENT", "Visible cleartext must be CONSEQUENT")

    b_labels: set[str] = set()
    for record in data["uncertainties"]:
        label = record["label"]
        require(label not in b_labels, f"Duplicate uncertainty label: {label}")
        b_labels.add(label)
        require(label in key and record["value"] == key[label], f"Uncertainty value mismatch: {label}")
        require(integer(record["occurrences"], "uncertainty occurrences") == frequencies[label],
                f"Uncertainty frequency mismatch: {label}")
        alternatives = json.loads(record["alternatives"])
        require(isinstance(alternatives, list) and bool(alternatives)
                and all(isinstance(item, str) for item in alternatives),
                f"Alternatives must be a JSON string list: {label}")
        require(len(alternatives) == len(set(alternatives)), f"Duplicate contextual alternatives: {label}")
        if label in OPEN_ALTERNATIVES:
            require(set(alternatives) == OPEN_ALTERNATIVES[label], f"Explicit alternatives were changed or omitted: {label}")
            require(record["status"] == "open_alternatives", f"Open alternative was relabeled: {label}")
        else:
            require(alternatives == [key[label]], f"Contextual proposal does not match the key: {label}")
            expected_status = "empty_or_punctuation" if key[label] in {"", ","} else "contextual"
            require(record["status"] == expected_status, f"Contextual status differs: {label}")
        require(bool(record["status"].strip()) and bool(record["note"].strip()),
                f"Missing uncertainty qualification: {label}")
    require(b_labels == contextual_labels and len(b_labels) == 48, "Incomplete class-B uncertainty register")

    readings = data["readings"]
    require(isinstance(readings, list) and len(readings) == 24, "Expected 24 editorial row readings")
    for number, record in enumerate(readings, 1):
        require(isinstance(record, dict) and {"row", "text", "note"} <= set(record),
                f"Malformed editorial reading row: {number}")
        require(integer(record["row"], "reading row") == number, "Editorial reading rows are out of order")
        require(isinstance(record["text"], str) and isinstance(record["note"], str),
                f"Invalid editorial text or note: row {number}")
    changes = data["changes"]
    require(len(changes) == 29, "Expected 29 editorial intervention blocks")
    by_row: dict[int, list[dict[str, str]]] = {number: [] for number in range(1, 25)}
    for record in changes:
        row = integer(record["row"], "intervention row")
        require(row in by_row, f"Intervention row out of range: {row}")
        by_row[row].append(record)
    for number in range(1, 25):
        candidate = normalize(literal_rows[number - 1])
        target = normalize(readings[number - 1]["text"])
        row_changes = sorted(by_row[number], key=lambda record: integer(record["candidate_start_1based"], "candidate start"))
        pos = 0
        pieces: list[str] = []
        for change in row_changes:
            start = integer(change["candidate_start_1based"], "candidate start") - 1
            end = integer(change["candidate_end_exclusive_1based"], "candidate end") - 1
            read_start = integer(change["reading_start_1based"], "reading start") - 1
            read_end = integer(change["reading_end_exclusive_1based"], "reading end") - 1
            require(pos <= start <= end <= len(candidate), f"Invalid or overlapping edit coordinates: row {number}")
            require(0 <= read_start <= read_end <= len(target), f"Invalid reading coordinates: row {number}")
            before, after = change["candidate"], change["reading"]
            require(candidate[start:end] == before, f"Edit source slice mismatch: row {number}")
            require(target[read_start:read_end] == after, f"Edit reading slice mismatch: row {number}")
            operation = change["operation"]
            require((operation == "insert" and not before and bool(after))
                    or (operation == "delete" and bool(before) and not after)
                    or (operation == "replace" and bool(before) and bool(after) and before != after),
                    f"Edit operation / contents mismatch: row {number}")
            pieces.append(candidate[pos:start])
            require(len("".join(pieces)) == read_start,
                    f"Edit reading coordinate does not track preceding edits: row {number}")
            pieces.append(after)
            require(len("".join(pieces)) == read_end,
                    f"Edit reading end does not track replacement: row {number}")
            pos = end
        pieces.append(candidate[pos:])
        require("".join(pieces) == target, f"Editorial replay fails: row {number}")

    reading = data["reading"]
    require(isinstance(reading, dict), "Malformed reading.json")
    for name in ("introduction", "translation_note"):
        require(isinstance(reading.get(name), str) and bool(reading[name].strip()), f"Missing {name} in reading.json")
    for name in ("french_paragraphs", "english_paragraphs"):
        require(isinstance(reading.get(name), list) and bool(reading[name])
                and all(isinstance(item, str) and bool(item.strip()) for item in reading[name]),
                f"Invalid {name} in reading.json")
    require(normalize("".join(reading["french_paragraphs"])) == normalize("".join(record["text"] for record in readings)),
            "French paragraphs differ from the 24 editorial row readings")
    supporting = _supporting_checks(root, data)
    report = {
        "pass": True, "rows": 24, "units": 1310, "cipher_units": 1300,
        "cleartext_units": 10, "cipher_labels": 155, "cleartext_labels": 8,
        "singleton_cipher_labels": 50, "evidence_classes": dict(sorted(classes.items())),
        "contextual_labels": 48, "explicit_alternative_labels": 6,
        "editorial_interventions_replayed": 29,
        "target_unresolved": True, "french_paragraphs_match_rows": True,
        "supporting_evidence": supporting,
    }
    return data, report


def _alignment_bytes(data: dict) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(["row", "candidate", "reading", "intervention_note"])
    for number, (literal, reading) in enumerate(zip(data["literal"].splitlines(), data["readings"]), 1):
        writer.writerow([number, literal, reading["text"], reading["note"]])
    return buffer.getvalue().encode("utf-8")


def _reading_text(data: dict) -> str:
    reading = data["reading"]
    parts = ["# Marmont letter: proposed reading", "", reading["introduction"], "",
             "## French editorial reading", "", "\n\n".join(reading["french_paragraphs"]), "",
             "## English translation", "", reading["translation_note"], "",
             "\n\n".join(reading["english_paragraphs"]), "",
             "## Row alignment", "",
             "The literal rows below are direct key output. The French reading applies the explicit "
             "editorial interventions in [editorial_interventions.tsv](../inputs/editorial_interventions.tsv). "
             "Its character coordinates use uppercase A–Z after removing accents, spaces and punctuation; "
             "the unresolved TARGET marker occupies one coordinate (¤). "
             "[uncertainties.tsv](../inputs/uncertainties.tsv) retains the contextual key assignments.", ""]
    for number, (literal, row) in enumerate(zip(data["literal"].splitlines(), data["readings"]), 1):
        parts.extend([f"### Row {number}", "", f"Literal: `{literal}`", "",
                      f"Editorial French: {row['text']}", "", row["note"], ""])
    return "\n".join(parts).rstrip() + "\n"


def build(root: Path, out: Path) -> dict:
    """Build only solution text outputs; never mutate inputs or source files."""
    data, report = validate(root)
    destination = Path(out) / "solution"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "literal.txt").write_bytes(data["literal"].encode("utf-8"))
    (destination / "reading.md").write_bytes(_reading_text(data).encode("utf-8"))
    (destination / "reading_alignment.tsv").write_bytes(_alignment_bytes(data))
    return {**report, "files": list(TEXT_OUTPUTS)}


def verify(root: Path) -> dict:
    """Validate inputs, independently join tokens, and regenerate all text."""
    root = Path(root)
    _, report = validate(root)
    with (root / "inputs/key.tsv").open(encoding="utf-8", newline="") as handle:
        lookup = {record["label"]: record["value"] for record in csv.DictReader(handle, delimiter="\t")}
    stream = (root / "inputs/transcription.txt").read_text(encoding="utf-8").splitlines()
    reference = "\n".join("".join(map(lookup.__getitem__, row.split())) for row in stream) + "\n"
    require(reference.encode("utf-8") == (root / "solution/literal.txt").read_bytes(),
            "Independent token / key rendering differs from solution/literal.txt")
    with tempfile.TemporaryDirectory(prefix="marmont-text-") as folder:
        destination = Path(folder)
        build(root, destination)
        for relative in TEXT_OUTPUTS:
            require((root / relative).read_bytes() == (destination / relative).read_bytes(),
                    f"Regenerated text differs: {relative}")
    return {**report, "independent_literal_byte_match": True,
            "regenerated_text_files": len(TEXT_OUTPUTS)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ignored(relative: PurePosixPath) -> bool:
    return (relative.parts[0] in {"results", ".venv"}
            or "__pycache__" in relative.parts or relative.name in {".DS_Store", "Thumbs.db"})


def verify_manifest(root: Path) -> dict:
    root = Path(root).resolve()
    path = root / "SHA256SUMS"
    require(path.is_file() and not path.is_symlink(), "Missing or unsafe SHA256SUMS")
    listed: dict[str, str] = {}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        require(match is not None, f"Malformed SHA256SUMS line {number}")
        digest, name = match.groups()
        relative = PurePosixPath(name)
        require(not relative.is_absolute() and ".." not in relative.parts
                and relative.as_posix() == name and "\\" not in name,
                f"Unsafe manifest path: {name}")
        require(name != "SHA256SUMS" and not _ignored(relative), f"Excluded path appears in manifest: {name}")
        require(name not in listed, f"Duplicate manifest entry: {name}")
        listed[name] = digest.lower()
    require(bool(listed), "Empty SHA256SUMS")
    actual: set[str] = set()
    for file in root.rglob("*"):
        relative = PurePosixPath(file.relative_to(root).as_posix())
        if _ignored(relative) or relative.as_posix() == "SHA256SUMS":
            continue
        require(not file.is_symlink(), f"Symlink in package: {relative}")
        if file.is_file():
            actual.add(relative.as_posix())
    missing = sorted(set(listed) - actual)
    unlisted = sorted(actual - set(listed))
    require(not missing, "Manifest files missing: " + ", ".join(missing[:8]))
    require(not unlisted, "Unlisted package files: " + ", ".join(unlisted[:8]))
    for name, expected in listed.items():
        require(sha256(root / name) == expected, f"SHA-256 mismatch: {name}")
    return {"pass": True, "listed_files": len(listed), "exact_file_inventory": True}


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value is None:
                continue
            if key == "id" or (tag == "a" and key == "name"):
                require(value not in self.ids, f"Duplicate HTML anchor: {value}")
                self.ids.add(value)
            if key in {"href", "src", "poster"}:
                self.links.append((key, value))

    handle_startendtag = handle_starttag


def verify_portal(root: Path) -> dict:
    root = Path(root).resolve()
    source = root / "START_HERE.html"
    document = _Links()
    document.feed(source.read_text(encoding="utf-8"))
    checked = external = 0
    parsed_documents = {source: document}
    for attribute, value in document.links:
        url = urlsplit(value)
        if url.scheme or url.netloc:
            require(url.scheme in {"https", "http"}, f"Unexpected portal URL scheme: {url.scheme}")
            require(attribute == "href", "Portal media must be available offline")
            external += 1
            continue
        relative = unquote(url.path)
        require(not relative.startswith("/"), f"Absolute local portal path: {value}")
        target = (source.parent / relative).resolve() if relative else source
        require(target.is_relative_to(root), f"Portal link leaves the package: {value}")
        require(target.is_file(), f"Broken portal link: {value}")
        if url.fragment and target.suffix.lower() in {".html", ".htm"}:
            if target not in parsed_documents:
                parser = _Links()
                parser.feed(target.read_text(encoding="utf-8"))
                parsed_documents[target] = parser
            require(unquote(url.fragment) in parsed_documents[target].ids, f"Missing portal anchor: {value}")
        checked += 1
    from . import portal
    with tempfile.TemporaryDirectory(prefix="marmont-portal-") as folder:
        destination = Path(folder)
        build(root, destination)
        portal.build(root, destination)
        require((destination / "START_HERE.html").read_bytes() == source.read_bytes(),
                "Regenerated START_HERE.html differs")
    return {"pass": True, "local_links_checked": checked,
            "external_references_not_fetched": external, "regenerated_html_byte_match": True}


def compare_generated(root: Path, out: Path, images: bool) -> dict:
    """Compare regenerated text bytes and, in full mode, every image pixel."""
    root, out = Path(root), Path(out)
    for relative in TEXT_OUTPUTS:
        require((out / relative).read_bytes() == (root / relative).read_bytes(), f"Reproduced text differs: {relative}")
    count = len(TEXT_OUTPUTS)
    pixel_count = 0
    if images:
        from PIL import Image
        for folder in ("glyphs", "views"):
            supplied = {file.relative_to(root).as_posix() for file in (root / folder).rglob("*") if file.is_file()}
            generated = {file.relative_to(out).as_posix() for file in (out / folder).rglob("*") if file.is_file()}
            require(supplied == generated, f"Reproduced {folder} inventory differs")
            for relative in sorted(generated):
                if relative.lower().endswith(".png"):
                    with Image.open(root / relative) as original, Image.open(out / relative) as replica:
                        require(original.mode == replica.mode and original.size == replica.size
                                and original.tobytes() == replica.tobytes(),
                                f"Reproduced image pixels differ: {relative}")
                    pixel_count += 1
                else:
                    require((out / relative).read_bytes() == (root / relative).read_bytes(),
                            f"Reproduced data differs: {relative}")
                    count += 1
        require((out / "START_HERE.html").read_bytes() == (root / "START_HERE.html").read_bytes(),
                "Reproduced START_HERE.html differs")
        count += 1
    return {"pass": True, "text_files_byte_compared": count, "images_pixel_compared": pixel_count}


def safe_results_path(root: Path, requested: Path, directory: bool = True) -> Path:
    """CLI writes are restricted to results/ and cannot follow symlinks."""
    root = Path(root).resolve()
    requested = Path(requested)
    path = requested if requested.is_absolute() else root / requested
    destination = path.resolve()
    results = root / "results"
    require(destination.is_relative_to(results) and destination != results,
            "Output must be below this package's results/ directory")
    relative = path.absolute().relative_to(root)
    current = root
    for part in relative.parts:
        current = current / part
        require(not current.is_symlink(), "Output path contains a symlink")
    if destination.exists():
        require(destination.is_dir() if directory else destination.is_file(), "Output has the wrong file type")
        if directory:
            require(not any(file.is_symlink() for file in destination.rglob("*")),
                    "Output directory contains a symlink")
    return destination
