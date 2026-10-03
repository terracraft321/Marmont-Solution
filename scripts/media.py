#!/usr/bin/env python3
"""Rebuild and independently check the solution's native-pixel image evidence.

Coordinates use a top-left origin, with left/top included and right/bottom
excluded. Glyphs are black, binary-alpha views of selected source pixels at a
single threshold. No pixels are reconstructed or resampled in the glyphs,
grayscale companions, source contexts, row crops, or token crops.
"""
from __future__ import annotations

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps


SHEET_COLUMNS = 10
SHEET_CELL_WIDTH = 144
SHEET_CELL_HEIGHT = 115
SHEET_MARGIN = 20
SHEET_HEADER = 80
SHEET_FOOTER = 75

GLYPH_COLUMNS = [
    "label", "file", "source_unit", "occurrences", "value", "glyph_height_px",
    "flag", "glyph_width_px", "png_height_px", "png_width_px", "raw_file",
    "source_box_ltrb", "source_context", "context_box_ltrb",
    "excluded_rectangles_ltrb", "defect_sites", "note",
]
ROW_COLUMNS = ["row", "file", "left", "top", "right", "bottom", "width", "height"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def _write_tsv(path: Path, columns: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _relative_path(value: str, prefix: str) -> str:
    path = PurePosixPath(value)
    _require(not path.is_absolute() and ".." not in path.parts, f"Unsafe image path: {value}")
    _require(path.parts[0] == prefix and path.suffix == ".png", f"Unexpected image path: {value}")
    _require("\\" not in value, f"Unexpected image path: {value}")
    return value


def _box(value: list[int] | tuple[int, ...], size: tuple[int, int], name: str) -> tuple[int, int, int, int]:
    _require(len(value) == 4 and all(type(v) is int for v in value), f"Invalid box: {name}")
    left, top, right, bottom = value
    _require(0 <= left < right <= size[0] and 0 <= top < bottom <= size[1], f"Box outside plate: {name}")
    return left, top, right, bottom


def _inputs(root: Path) -> tuple[Image.Image, dict[str, Any], dict[str, dict[str, str]], list[dict[str, Any]], list[dict[str, Any]]]:
    meta = json.loads((root / "inputs/glyph_selection.json").read_text(encoding="utf-8"))
    _require(meta["source_image"] == "sources/cipher_plate.png", "Unexpected source image path")
    source_path = root / meta["source_image"]
    _require(hashlib.sha256(source_path.read_bytes()).hexdigest() == meta["source_image_sha256"], "Source image checksum differs")
    with Image.open(source_path) as source:
        plate = source.convert("L")
    _require(plate.size == tuple(meta["source_size_px"]) == (1051, 1246), "Unexpected source dimensions")
    _require(meta["threshold"] == 225 and meta["padding_px"] == 3, "Unexpected glyph transform")
    _require(meta["threshold_operator"] == "<=", "Unexpected glyph threshold operator")

    key_rows = _read_tsv(root / "inputs/key.tsv")
    key = {row["label"]: row for row in key_rows}
    _require(len(key_rows) == len(key) == 163, "Key must contain 163 unique labels")
    stream = [line.split() for line in (root / "inputs/transcription.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    _require(len(stream) == 24 and sum(map(len, stream)) == 1310, "Unexpected transcription dimensions")
    counts = Counter(label for line in stream for label in line)
    _require(set(counts) == set(key), "Transcription/key coverage differs")
    for label, entry in key.items():
        _require(int(entry["occurrences"]) == counts[label], f"Occurrence count differs: {label}")

    units: list[dict[str, Any]] = []
    addresses: set[tuple[int, int]] = set()
    for source_unit in _read_tsv(root / "inputs/units.tsv"):
        row = int(source_unit["row"])
        token = int(source_unit["token"])
        _require(1 <= row <= len(stream) and 1 <= token <= len(stream[row - 1]), "Unit address outside transcription")
        _require((row, token) not in addresses, f"Duplicate unit address: r{row}:t{token}")
        addresses.add((row, token))
        label = source_unit["label"]
        _require(label == stream[row - 1][token - 1], f"Unit label differs: r{row}:t{token}")
        _require(source_unit["value"] == key[label]["value"], f"Unit key value differs: r{row}:t{token}")
        bounds = _box([int(source_unit[name]) for name in ("left", "top", "right", "bottom")], plate.size, f"r{row}:t{token}")
        units.append({"row": row, "token": token, "label": label, "box": bounds,
                      "file": f"views/units/r{row:02d}_t{token:02d}.png"})
    _require(len(units) == 1310, "Expected exactly 1310 native token crops")
    units.sort(key=lambda unit: (unit["row"], unit["token"]))

    selections = meta["selections"]
    expected_labels = {label for label in key if not label.startswith("@")}
    _require(len(selections) == len(expected_labels) == 155, "Expected 155 cipher glyph selections")
    _require({item["label"] for item in selections} == expected_labels, "Glyph selection/key coverage differs")
    paths: list[str] = []
    for item in selections:
        label = item["label"]
        for name in ("file", "raw_file", "context_file"):
            paths.append(_relative_path(item[name], "glyphs"))
        bounds = _box(item["source_box_ltrb"], plate.size, label)
        context = _box(item["context_box_ltrb"], plate.size, label + " context")
        _require(context[0] <= bounds[0] < bounds[2] <= context[2] and context[1] <= bounds[1] < bounds[3] <= context[3], f"Glyph lies outside context: {label}")
        for excluded in item["excluded_rectangles_ltrb"]:
            _box(excluded, plate.size, label + " exclusion")
        row_text, token_text = item["source_unit"].split(":")
        row, token = int(row_text.removeprefix("r")), int(token_text.removeprefix("t"))
        _require((row, token) in addresses and stream[row - 1][token - 1] == label, f"Glyph source address differs: {label}")
    _require(len({path.casefold() for path in paths}) == len(paths), "Image filenames collide")
    placements = json.loads((root / "inputs/glyph_sheet_placements.json").read_text(encoding="utf-8"))
    _require(placements == _placements(selections, key), "Contact-sheet placements differ from the stated layout")
    return plate, meta, key, units, placements


def _save_png(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Copy only pixels, excluding inherited PNG metadata and ancillary chunks.
    clean = Image.frombytes(image.mode, image.size, image.tobytes())
    clean.save(path, format="PNG", optimize=False)


def _glyph_images(plate: Image.Image, item: dict[str, Any], threshold: int, pad: int) -> tuple[Image.Image, Image.Image, Image.Image]:
    left, top, right, bottom = item["source_box_ltrb"]
    original = plate.crop((left, top, right, bottom))
    raw = ImageOps.expand(original, border=pad, fill=255)
    alpha = Image.new("L", raw.size, 0)
    alpha.paste(original.point(lambda pixel: 255 if pixel <= threshold else 0), (pad, pad))
    draw = ImageDraw.Draw(alpha)
    for ex_left, ex_top, ex_right, ex_bottom in item["excluded_rectangles_ltrb"]:
        x0, y0 = max(left, ex_left), max(top, ex_top)
        x1, y1 = min(right, ex_right), min(bottom, ex_bottom)
        if x0 < x1 and y0 < y1:
            draw.rectangle((x0 - left + pad, y0 - top + pad, x1 - left + pad - 1, y1 - top + pad - 1), fill=0)
    glyph = Image.new("RGBA", raw.size, (0, 0, 0, 0))
    glyph.putalpha(alpha)
    context = plate.crop(tuple(item["context_box_ltrb"]))
    return glyph, raw, context


def _glyph_row(item: dict[str, Any], entry: dict[str, str], pad: int) -> dict[str, Any]:
    left, top, right, bottom = item["source_box_ltrb"]
    return {
        "label": item["label"], "file": item["file"], "source_unit": item["source_unit"],
        "occurrences": entry["occurrences"], "value": entry["value"],
        "glyph_height_px": bottom - top, "flag": item["flag"], "glyph_width_px": right - left,
        "png_height_px": bottom - top + 2 * pad, "png_width_px": right - left + 2 * pad,
        "raw_file": item["raw_file"], "source_box_ltrb": ",".join(map(str, item["source_box_ltrb"])),
        "source_context": item["context_file"], "context_box_ltrb": ",".join(map(str, item["context_box_ltrb"])),
        "excluded_rectangles_ltrb": json.dumps(item["excluded_rectangles_ltrb"], separators=(",", ":")),
        "defect_sites": ";".join(item["defect_sites"]), "note": item["note"],
    }


def _value_sort(value: str) -> tuple[int, str]:
    if len(value) == 1 and "A" <= value <= "Z":
        return 0, value
    if value.isalpha() and value.isascii():
        return 1, value
    if value == "":
        return 3, value
    if "UNRESOLVED" in value:
        return 4, value
    return 2, value


def _placements(selections: list[dict[str, Any]], key: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    ordered = sorted(selections, key=lambda item: (_value_sort(key[item["label"]]["value"]), item["label"]))
    result = []
    for index, item in enumerate(ordered):
        left, top, right, bottom = item["source_box_ltrb"]
        width, height = right - left + 6, bottom - top + 6
        cell_left = SHEET_MARGIN + (index % SHEET_COLUMNS) * SHEET_CELL_WIDTH
        cell_top = SHEET_HEADER + (index // SHEET_COLUMNS) * SHEET_CELL_HEIGHT
        result.append({"label": item["label"], "file": item["file"],
                       "x": cell_left + (SHEET_CELL_WIDTH - width) // 2,
                       "y": cell_top + 23 + (62 - height) // 2,
                       "width": width, "height": height})
    return result


def _bitmap_font() -> ImageFont.ImageFont:
    # Older Pillow uses this bitmap font as load_default(); newer Pillow exposes
    # it explicitly. Avoid the optional default TrueType font and system fonts.
    factory = getattr(ImageFont, "load_default_imagefont", ImageFont.load_default)
    return factory()


def _sheet(placements: list[dict[str, Any]], selections: list[dict[str, Any]], key: dict[str, dict[str, str]], glyphs: dict[str, Image.Image]) -> Image.Image:
    row_count = (len(placements) + SHEET_COLUMNS - 1) // SHEET_COLUMNS
    size = (2 * SHEET_MARGIN + SHEET_COLUMNS * SHEET_CELL_WIDTH, SHEET_HEADER + row_count * SHEET_CELL_HEIGHT + SHEET_FOOTER)
    sheet = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(sheet)
    font = _bitmap_font()
    title = Image.new("RGB", (600, 15), "white")
    ImageDraw.Draw(title).text((0, 0), "MARMONT: CIPHER KEY GLYPHS", font=font, fill=(20, 28, 35))
    sheet.paste(title.resize((1200, 30), resample=Image.Resampling.NEAREST), (SHEET_MARGIN, 12))
    draw.text((SHEET_MARGIN, 47), "155 cipher labels | one selected source occurrence per label | native pixel size", font=font, fill=(50, 55, 60))
    draw.text((SHEET_MARGIN, 62), "Each cell: key value, glyph, cipher label, source address. * marks a recorded source limitation.", font=font, fill=(50, 55, 60))
    lookup = {item["label"]: item for item in selections}
    for index, placement in enumerate(placements):
        label = placement["label"]
        item = lookup[label]
        cell_left = SHEET_MARGIN + (index % SHEET_COLUMNS) * SHEET_CELL_WIDTH
        cell_top = SHEET_HEADER + (index // SHEET_COLUMNS) * SHEET_CELL_HEIGHT
        draw.rectangle((cell_left, cell_top, cell_left + SHEET_CELL_WIDTH - 1, cell_top + SHEET_CELL_HEIGHT - 1), outline=(220, 223, 226))
        value = key[label]["value"].replace("⟦", "[").replace("⟧", "]") or "(empty)"
        label_text = label + ("*" if item["flag"] else "")
        for text, y in ((value, cell_top + 6), (label_text, cell_top + 87), (item["source_unit"], cell_top + 101)):
            bounds = draw.textbbox((0, 0), text, font=font)
            width = bounds[2] - bounds[0]
            draw.text((cell_left + (SHEET_CELL_WIDTH - width) // 2, y), text, font=font, fill=(25, 30, 35))
        glyph = glyphs[label]
        sheet.paste(glyph, (placement["x"], placement["y"]), glyph)
    footer = SHEET_HEADER + row_count * SHEET_CELL_HEIGHT + 13
    draw.text((SHEET_MARGIN, footer), "Threshold: source grayscale <= 225; padding: 3 px. No glyph is resized, redrawn, or sharpened.", font=font, fill=(50, 55, 60))
    draw.text((SHEET_MARGIN, footer + 15), "Empty key values are printed as (empty); unresolved marker brackets are simplified for this bitmap font.", font=font, fill=(50, 55, 60))
    draw.text((SHEET_MARGIN, footer + 30), "See glyphs/glyphs.tsv for exact values, coordinates, exclusions, and source limitations; inputs/key.tsv includes cleartext labels.", font=font, fill=(50, 55, 60))
    return sheet


def _row_bounds(units: list[dict[str, Any]], size: tuple[int, int]) -> list[dict[str, Any]]:
    rows = []
    for row in range(1, 25):
        group = [unit["box"] for unit in units if unit["row"] == row]
        left = max(0, min(box[0] for box in group) - 8)
        top = max(0, min(box[1] for box in group) - 4)
        right = min(size[0], max(box[2] for box in group) + 8)
        bottom = min(size[1], max(box[3] for box in group) + 4)
        rows.append({"row": row, "file": f"views/rows/r{row:02d}.png", "left": left, "top": top,
                     "right": right, "bottom": bottom, "width": right - left, "height": bottom - top})
    return rows


def build(root: Path, out: Path) -> dict[str, Any]:
    """Write glyphs/ and views/ below out, using only inputs and the source plate."""
    root, out = Path(root), Path(out)
    plate, meta, key, units, placements = _inputs(root)
    glyph_table, glyph_images, files = [], {}, []
    for item in meta["selections"]:
        glyph, raw, context = _glyph_images(plate, item, meta["threshold"], meta["padding_px"])
        glyph_images[item["label"]] = glyph
        for image, name in ((glyph, "file"), (raw, "raw_file"), (context, "context_file")):
            _save_png(image, out / item[name])
            files.append(item[name])
        glyph_table.append(_glyph_row(item, key[item["label"]], meta["padding_px"]))
    _write_tsv(out / "glyphs/glyphs.tsv", GLYPH_COLUMNS, glyph_table)
    _save_png(_sheet(placements, meta["selections"], key, glyph_images), out / "glyphs/key_glyphs_sheet.png")
    files += ["glyphs/glyphs.tsv", "glyphs/key_glyphs_sheet.png"]
    for unit in units:
        _save_png(plate.crop(unit["box"]), out / unit["file"])
        files.append(unit["file"])
    rows = _row_bounds(units, plate.size)
    for row in rows:
        _save_png(plate.crop(tuple(row[name] for name in ("left", "top", "right", "bottom"))), out / row["file"])
        files.append(row["file"])
    _write_tsv(out / "views/rows.tsv", ROW_COLUMNS, rows)
    files.append("views/rows.tsv")
    return {"pass": True, "status": "PASS", "glyphs": 155, "grayscale_companions": 155,
            "source_contexts": 155, "unit_crops": 1310, "row_crops": 24, "contact_sheets": 1,
            "files": sorted(files)}


def _compare_image(path: Path, expected: Image.Image) -> Image.Image:
    with Image.open(path) as source:
        actual = source.copy()
    _require(actual.mode == expected.mode and actual.size == expected.size and actual.tobytes() == expected.tobytes(), f"Image pixels differ: {path.name}")
    _require(not actual.info, f"Unexpected image metadata: {path.name}")
    return actual


def verify(root: Path) -> dict[str, Any]:
    """Check all outputs against source pixels, key, transcription, and coordinates.

    Glyph raw pixels and alpha are checked directly, independently of the glyph
    builder. PNG encoding bytes are deliberately not used for pixel comparison.
    """
    root = Path(root)
    plate, meta, key, units, placements = _inputs(root)
    source_pixels = plate.load()
    pad, threshold = meta["padding_px"], meta["threshold"]
    expected_paths: set[str] = {"glyphs/glyphs.tsv", "glyphs/key_glyphs_sheet.png", "views/rows.tsv"}
    expected_table = [_glyph_row(item, key[item["label"]], pad) for item in meta["selections"]]
    actual_table = _read_tsv(root / "glyphs/glyphs.tsv")
    _require(actual_table == [{key: str(value) for key, value in row.items()} for row in expected_table], "Glyph TSV differs from input selections/key")
    glyph_images = {}
    defect_labels = []
    for item in meta["selections"]:
        label = item["label"]
        left, top, right, bottom = item["source_box_ltrb"]
        with Image.open(root / item["file"]) as image:
            glyph = image.copy()
        with Image.open(root / item["raw_file"]) as image:
            raw = image.copy()
        expected_size = (right - left + 2 * pad, bottom - top + 2 * pad)
        _require(glyph.mode == "RGBA" and raw.mode == "L" and glyph.size == raw.size == expected_size, f"Glyph image dimensions/modes differ: {label}")
        _require(not glyph.info and not raw.info, f"Unexpected glyph metadata: {label}")
        raw_pixels, glyph_pixels = raw.load(), glyph.load()
        for y in range(raw.height):
            for x in range(raw.width):
                sx, sy = left + x - pad, top + y - pad
                inside = pad <= x < raw.width - pad and pad <= y < raw.height - pad
                expected_raw = source_pixels[sx, sy] if inside else 255
                _require(raw_pixels[x, y] == expected_raw, f"Grayscale source pixel differs: {label} ({x},{y})")
                excluded = any(el <= sx < er and et <= sy < eb for el, et, er, eb in item["excluded_rectangles_ltrb"])
                expected_alpha = 255 if inside and not excluded and expected_raw <= threshold else 0
                _require(glyph_pixels[x, y] == (0, 0, 0, expected_alpha), f"Glyph alpha/source pixel differs: {label} ({x},{y})")
        _require(glyph.getchannel("A").getbbox() == (pad, pad, glyph.width - pad, glyph.height - pad), f"Glyph does not have exactly three pixels of padding: {label}")
        _compare_image(root / item["context_file"], plate.crop(tuple(item["context_box_ltrb"])))
        glyph_images[label] = glyph
        expected_paths.update(item[name] for name in ("file", "raw_file", "context_file"))
        if item["defect_sites"]:
            defect_labels.append(label)
    _require(set(defect_labels) == {"THETA_BLOTTED", "x_BLOTTED"}, "Defect-site coverage differs")
    for unit in units:
        _compare_image(root / unit["file"], plate.crop(unit["box"]))
        expected_paths.add(unit["file"])
    expected_rows = _row_bounds(units, plate.size)
    _require(_read_tsv(root / "views/rows.tsv") == [{key: str(value) for key, value in row.items()} for row in expected_rows], "Row geometry TSV differs")
    for row in expected_rows:
        _compare_image(root / row["file"], plate.crop(tuple(row[name] for name in ("left", "top", "right", "bottom"))))
        expected_paths.add(row["file"])
    sheet = _compare_image(root / "glyphs/key_glyphs_sheet.png", _sheet(placements, meta["selections"], key, glyph_images))
    for placement in placements:
        glyph = glyph_images[placement["label"]]
        white = Image.new("RGBA", glyph.size, "white")
        white.alpha_composite(glyph)
        x, y = placement["x"], placement["y"]
        actual = sheet.crop((x, y, x + glyph.width, y + glyph.height))
        _require(actual.tobytes() == white.convert("RGB").tobytes(), f"Contact-sheet glyph pixels differ: {placement['label']}")
    actual_paths = {str(path.relative_to(root).as_posix()) for prefix in ("glyphs", "views") for path in (root / prefix).rglob("*") if path.is_file()}
    _require(actual_paths == expected_paths, "Unexpected or missing files in glyphs/views")
    return {
        "pass": True, "status": "PASS", "glyphs": 155, "grayscale_companions": 155,
        "source_contexts": 155, "unit_crops": 1310, "row_crops": 24, "contact_sheets": 1,
        "checked_image_files": 1800, "checked_media_files": len(expected_paths),
        "cleartext_labels_skipped": 8, "threshold": threshold, "padding_px": pad,
        "selected_defect_labels": sorted(defect_labels),
        "checks": ["key/transcription/address/coordinate coverage", "source checksum and dimensions",
                   "all grayscale glyph pixels and white padding against source plate", "all black glyph pixels and binary alpha against source threshold/exclusions",
                   "all native source contexts, token crops, and row crops", "exact glyph TSV and row geometry",
                   "contact-sheet layout, text, and native glyph pixels", "image metadata absence and exact output coverage"],
    }
