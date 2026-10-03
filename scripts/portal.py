"""Build the deterministic, entirely local HTML reader for this solution.

The reader is a view over the supplied data, not a source of decipherment
decisions. It needs only the Python standard library. Its links are relative
to the generated output directory, so the page also works in a reproduced tree.
"""

from __future__ import annotations

import csv
import html
import json
import re
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def _number(value: Any) -> int:
    match = re.search(r"\d+", str(value))
    if not match:
        raise ValueError(f"Expected row or token number, received {value!r}")
    return int(match.group())


def _relpath(value: str) -> str:
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or ":" in value:
        raise ValueError(f"Expected a package-relative path, received {value!r}")
    return path.as_posix()


def _link(path: str, label: str, css: str = "") -> str:
    target = path if path.startswith("#") else _relpath(path)
    attr = f' class="{_escape(css)}"' if css else ""
    return f'<a href="{_escape(target)}"{attr}>{_escape(label)}</a>'


def _paragraphs(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "\n".join(_paragraphs(item) for item in value)
    if not isinstance(value, str):
        raise ValueError("Reading paragraphs must be text or a list of text")
    return "\n".join(
        f"<p>{_escape(part.strip())}</p>"
        for part in re.split(r"\n\s*\n", value)
        if part.strip()
    )


def _display_value(value: str) -> str:
    return "∅ (empty output)" if value == "" else value


def _find_generated(root: Path, out: Path, relative: str) -> Path:
    generated = out / relative
    return generated if generated.is_file() else root / relative


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.paths: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.paths.add(value)


_STYLE = """
:root{color-scheme:light;--ink:#172c40;--muted:#526171;--paper:#f7f4ed;
--surface:#fffdf9;--line:#d8d7ce;--accent:#2d645f;--amber:#82551c;
--amber-bg:#fbf0d9;--rust:#8b493a;--rust-bg:#f7e9e3;--radius:9px}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:1.25rem}
body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,
-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--accent);text-underline-offset:3px}a:hover{color:var(--ink)}
a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible,
summary:focus-visible{outline:3px solid #ca9848;outline-offset:4px}
.wrap{max-width:1180px;margin:auto;padding:0 32px}
.skip{position:absolute;left:16px;top:-100px;background:white;padding:8px;z-index:5}
.skip:focus{top:8px}.masthead{border-bottom:1px solid var(--line);padding:21px 0}
.masthead .wrap{display:flex;justify-content:space-between;gap:1rem;align-items:center}
.eyebrow{font-size:.72rem;font-weight:750;letter-spacing:.13em;text-transform:uppercase}
.quiet{color:var(--muted)}.edition{font-size:.78rem;color:var(--muted)}
.hero{display:grid;grid-template-columns:minmax(0,1fr) 260px;gap:64px;padding:52px 0 38px}
h1,h2,h3{font-family:Georgia,"Times New Roman",serif;font-weight:500;line-height:1.15}
h1{font-size:clamp(2.5rem,5vw,4.4rem);letter-spacing:-.035em;margin:.1em 0 .3em}
.deck{font-size:1.17rem;max-width:650px;line-height:1.5;margin:0 0 20px}
.credit{font-size:.87rem;color:var(--muted)}.hero figure{margin:0;align-self:start}
.hero figure a{display:block;border:1px solid var(--line);background:white;padding:8px;
box-shadow:0 7px 22px #172c400c}.hero img{display:block;width:100%;height:auto}
figcaption{font-size:.75rem;color:var(--muted);line-height:1.4;margin-top:9px}
.counts{display:flex;gap:25px;flex-wrap:wrap;border-top:1px solid var(--line);
padding-top:19px;margin-top:25px}.counts b{display:block;font:1.8rem/1.1 Georgia,serif}
.counts span{font-size:.72rem;color:var(--muted)}
nav{display:flex;gap:7px;flex-wrap:wrap;padding:0 0 22px;border-bottom:1px solid var(--line)}
nav a{padding:7px 13px;border:1px solid var(--line);border-radius:30px;text-decoration:none;
font-size:.83rem;background:var(--surface)}nav a:hover{border-color:var(--accent)}
main section{padding:37px 0;border-bottom:1px solid var(--line)}
h2{font-size:2rem;letter-spacing:-.015em;margin:0 0 15px}h3{font-size:1.3rem;margin:0 0 16px}
p{margin:0 0 1em}.section-intro{max-width:830px;font-size:.94rem;color:var(--muted)}
.note{border-left:3px solid #c18b3d;padding:14px 18px;background:#f0ece2;font-size:.88rem;
margin:19px 0 24px}.note p:last-child{margin-bottom:0}
.reading-grid{display:grid;grid-template-columns:1fr 1fr;gap:39px;margin-top:26px}
.reading-grid article{min-width:0}.reading-grid article+article{border-left:1px solid var(--line);
padding-left:39px}.reading-grid p{font:1.04rem/1.78 Georgia,"Times New Roman",serif}
.language{font:700 .72rem/1.4 system-ui,sans-serif;letter-spacing:.12em;text-transform:uppercase;
color:var(--accent);margin:0 0 14px}.reading-notes{font-size:.85rem;color:var(--muted);
margin-top:22px}.reading-notes p:last-child{margin-bottom:0}.file-links{font-size:.84rem;
display:flex;flex-wrap:wrap;gap:8px 19px;margin:16px 0 0}
details{border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)}
summary{cursor:pointer;padding:16px 19px;line-height:1.4;font-size:.93rem;font-weight:650}
summary::marker{color:var(--accent)}details[open]>summary{border-bottom:1px solid var(--line)}
.row-list{display:grid;gap:11px;margin-top:20px}.row-summary{display:inline-flex;
width:calc(100% - 24px);justify-content:space-between;align-items:center;gap:12px}
.row-summary small{color:var(--muted);font-weight:400;font-size:.77rem}
.row-body{padding:18px}.row-crop{display:block;border:1px solid var(--line);background:white;
padding:8px;margin-bottom:19px}.row-crop img{display:block;width:100%;height:auto;max-height:145px;
object-fit:contain;object-position:left center}.field-label{font-size:.65rem;font-weight:750;
text-transform:uppercase;letter-spacing:.1em;color:var(--muted);margin:14px 0 5px}
.row-reading{font:1.05rem/1.65 Georgia,"Times New Roman",serif;margin:0}
pre,code{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace}
.literal{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.8rem;line-height:1.65;
background:#f0f2ef;padding:11px 13px;border-radius:4px;margin:0}
.row-note{font-size:.8rem;color:var(--muted);margin:13px 0 18px}
.tokens{background:#f8f8f3}.tokens summary{font-size:.8rem;padding:10px 13px}
.token-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(104px,1fr));gap:8px;padding:13px}
.token{min-width:0;border:1px solid var(--line);background:var(--surface);border-radius:4px;
padding:8px;text-align:center;display:flex;flex-direction:column;gap:5px}
.token.B{border-color:#d7b16e;background:#fdf8eb}.token.C{border-color:#c99282;background:#fcf2ec}
.token.cleartext{background:#ecf2f1}.token-id{font-size:.65rem;color:var(--muted)}
.token-image{height:42px;display:flex;align-items:center;justify-content:center}
.token-image img{max-width:100%;max-height:42px;width:auto;height:auto;object-fit:contain}
.token-label{font-size:.63rem;line-height:1.3;overflow-wrap:anywhere;min-height:1.4em}
.token-value{font:700 .72rem/1.3 ui-monospace,monospace;overflow-wrap:anywhere}
.token-grade{font-size:.59rem;color:var(--muted);line-height:1.25;margin-top:auto}
.legend{font-size:.78rem;color:var(--muted);padding:0 13px 12px;margin:0}
.toolbar{padding:17px;display:flex;align-items:end;flex-wrap:wrap;gap:13px;border-bottom:1px solid var(--line)}
.toolbar label{font-size:.74rem;font-weight:650;display:block;margin-bottom:4px}
.search-field{flex:1;min-width:180px}input,select{font:inherit;font-size:.9rem;padding:9px 11px;
border:1px solid #9aa7a5;border-radius:4px;background:white;color:var(--ink);min-height:40px}
input{width:100%}select{max-width:100%}.table-count{font-size:.76rem;color:var(--muted);margin:0 0 8px}
.table-scroll{width:100%;overflow:auto}table{border-collapse:collapse;width:100%;font-size:.82rem}
th{text-align:left;font-size:.65rem;letter-spacing:.075em;text-transform:uppercase;
padding:12px 14px;background:#edf0eb;color:var(--muted);vertical-align:bottom}
td{padding:12px 14px;border-top:1px solid var(--line);vertical-align:top}
.key-table td{vertical-align:middle}.key-image{width:68px;min-width:68px;text-align:center}
.key-image img{height:auto;width:auto;max-width:49px;max-height:45px;object-fit:contain}
.key-label{font-size:.72rem;overflow-wrap:anywhere}.key-value{font-family:ui-monospace,monospace;
font-size:.8rem;overflow-wrap:anywhere}.key-context{font-size:.69rem;display:block;margin-top:4px}
.count-cell{text-align:right;font-variant-numeric:tabular-nums}.badge{display:inline-block;
font-size:.65rem;line-height:1.4;padding:3px 6px;border-radius:3px;background:#eaf0e9;color:#3b5c4a}
.badge.contextual,.badge.open{background:var(--amber-bg);color:var(--amber)}
.badge.defect{background:var(--rust-bg);color:var(--rust)}.badge.clear{background:#e9eeee;color:#4b6264}
.key-table tr:target{outline:2px solid #c18b3d;outline-offset:-2px;background:#fff6df}
.key-note{font-size:.72rem;color:var(--muted);max-width:375px;line-height:1.5;margin-top:5px}
.uncertainty-table td:first-child{font-family:ui-monospace,monospace;font-size:.7rem}
.uncertainty-table td{font-size:.8rem;line-height:1.5}.uncertainty-note{min-width:260px}
.files td:first-child{white-space:nowrap;font-family:ui-monospace,monospace;font-size:.75rem}
.reproduce-grid{display:grid;grid-template-columns:1fr 1fr;gap:25px}
.command-card{background:var(--surface);border:1px solid var(--line);padding:20px;border-radius:var(--radius)}
.command-card h3{font-size:1.2rem;margin-bottom:10px}.command-card p{font-size:.85rem;color:var(--muted)}
.command-card pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:.81rem;padding:13px;
background:#edf0eb;border-radius:4px;margin:12px 0 0}.path{font-size:.82rem}
.source-card{display:grid;grid-template-columns:160px 1fr;gap:25px;align-items:start;margin-top:22px}
.source-card img{max-width:100%;height:auto;border:1px solid var(--line);padding:5px;background:white}
.source-card p{font-size:.87rem;color:var(--muted)}footer{padding:25px 0 38px;font-size:.77rem;color:var(--muted)}
[hidden]{display:none!important}.noscript{font-size:.8rem;color:var(--muted);padding:0 17px}
@media(max-width:760px){.wrap{padding:0 20px}.hero{grid-template-columns:minmax(0,1fr) 135px;gap:23px;
padding-top:32px}h1{font-size:2.7rem}.deck{font-size:1rem}.hero figcaption{font-size:.65rem}
.counts{gap:19px}.counts b{font-size:1.5rem}.reading-grid{grid-template-columns:1fr;gap:26px}
.reading-grid article+article{padding:25px 0 0;border-left:0;border-top:1px solid var(--line)}
.reproduce-grid{grid-template-columns:1fr}.row-body{padding:13px}.row-summary small{max-width:130px;
text-align:right}.source-card{grid-template-columns:105px 1fr;gap:18px}th,td{padding:10px}
.key-note{min-width:200px}.key-label{min-width:125px}main section{padding:28px 0}}
@media(max-width:480px){.hero{grid-template-columns:1fr}.hero figure{display:none}h1{font-size:2.6rem}
.edition{max-width:100px;text-align:right}.counts{gap:25px}.source-card{grid-template-columns:85px 1fr}}
@media print{body{background:white;color:black;font-size:10pt}.wrap{max-width:none;padding:0}
nav,.skip,.toolbar,.token-grid,.tokens,.command-card pre{display:none}.hero{padding:10px 0;gap:30px;
grid-template-columns:1fr 130px}.hero h1{font-size:30pt}.counts b{font-size:18pt}
main section{padding:20px 0}a{color:inherit}details{break-inside:avoid}.row-crop img{max-height:95px}
.reading-grid p{font-size:10pt;line-height:1.55}.note{background:transparent}footer{padding:15px 0}}
"""


_SCRIPT = """
(() => {
  'use strict';
  const input = document.getElementById('key-search');
  const scope = document.getElementById('key-scope');
  const rows = Array.from(document.querySelectorAll('[data-key-entry]'));
  const counter = document.getElementById('key-count');
  const apply = () => {
    const query = input.value.trim().toLocaleLowerCase();
    let shown = 0;
    rows.forEach(row => {
      const textMatch = !query || row.dataset.search.includes(query);
      const scopeMatch = scope.value === 'all' || row.dataset[scope.value] === 'yes';
      row.hidden = !(textMatch && scopeMatch);
      if (!row.hidden) shown += 1;
    });
    counter.textContent = shown + ' of ' + rows.length + ' entries';
  };
  input.addEventListener('input', apply);
  scope.addEventListener('change', apply);
  const revealAnchor = () => {
    const name = window.location.hash.slice(1);
    if (!name) return;
    const target = document.getElementById(name);
    if (!target) return;
    if (target.hasAttribute('data-key-entry')) {
      input.value = '';
      scope.value = 'all';
      apply();
    }
    let node = target;
    while (node) {
      if (node.tagName === 'DETAILS') node.open = true;
      node = node.parentElement;
    }
    window.requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
  };
  window.addEventListener('hashchange', revealAnchor);
  apply();
  revealAnchor();
})();
"""


def build(root: Path, out: Path) -> dict[str, Any]:
    """Render START_HERE.html from canonical inputs and generated views.

    `root` is the package root. `out` is either that directory or the root of a
    reproduction. Core and media outputs must have been built before this call.
    No network requests or absolute paths are embedded in the page.
    """
    root, out = Path(root), Path(out)
    key = _read_tsv(root / "inputs/key.tsv")
    units = _read_tsv(root / "inputs/units.tsv")
    uncertainty = _read_tsv(root / "inputs/uncertainties.tsv")
    reading = json.loads((root / "inputs/reading.json").read_text(encoding="utf-8"))
    reading_rows = json.loads((root / "inputs/reading_rows.json").read_text(encoding="utf-8"))
    glyphs = _read_tsv(_find_generated(root, out, "glyphs/glyphs.tsv"))
    literal = _find_generated(root, out, "solution/literal.txt").read_text(encoding="utf-8").splitlines()
    if len(reading_rows) != len(literal):
        raise ValueError("Editorial reading and literal output must have the same row count")
    if len({row["label"] for row in key}) != len(key):
        raise ValueError("Duplicate key label")
    glyph_by_label = {row["label"]: row for row in glyphs}
    uncertain_by_label = {row["label"]: row for row in uncertainty}
    key_ids = {row["label"]: f"key-{index:03d}" for index, row in enumerate(key, 1)}
    units_by_row: dict[int, list[dict[str, str]]] = defaultdict(list)
    classes_by_label: dict[str, set[str]] = defaultdict(set)
    for unit in units:
        units_by_row[_number(unit["row"])].append(unit)
        classes_by_label[unit["label"]].add(unit["evidence_class"])
    contextual_count = sum("B" in classes for classes in classes_by_label.values())
    cipher_count = sum(not row["label"].startswith("@") for row in key)
    clear_count = len(key) - cipher_count
    alternatives = []
    for item in uncertainty:
        choices = json.loads(item.get("alternatives") or "[]")
        if not isinstance(choices, list):
            raise ValueError("Uncertainty alternatives must be a JSON list")
        if len(choices) > 1:
            alternatives.append((item, choices))

    key_html = []
    for entry in key:
        label = entry["label"]
        glyph = glyph_by_label.get(label)
        uncertain = uncertain_by_label.get(label, {})
        note = uncertain.get("note", "")
        classes = classes_by_label.get(label, set())
        is_contextual = "B" in classes
        is_open = len(json.loads(uncertain.get("alternatives") or "[]")) > 1 or label == "TARGET"
        if label.startswith("@"):
            image_cell = '<span class="quiet">Cleartext</span>'
            status = '<span class="badge clear">Visible cleartext</span>'
        else:
            if glyph is None:
                raise ValueError(f"Missing representative glyph for {label}")
            image_path = _relpath(glyph["file"])
            image_cell = (
                f'<a href="{_escape(image_path)}" title="Open glyph {_escape(label)}">'
                f'<img src="{_escape(image_path)}" alt="Cipher glyph {_escape(label)}" loading="lazy"></a>'
            )
            if label == "TARGET":
                status = '<span class="badge open">Unresolved</span>'
            elif is_open:
                status = '<span class="badge open">Open alternatives</span>'
            elif is_contextual:
                status = '<span class="badge contextual">Contextual</span>'
            elif "C" in classes:
                status = '<span class="badge defect">Includes affected ink</span>'
            else:
                status = '<span class="badge">Proposed mapping</span>'
        context = ""
        if glyph:
            source_id = glyph.get("source_unit", "")
            context = f'<span class="key-context">Sample: {_escape(source_id)}</span>'
            if glyph.get("source_context"):
                context += _link(glyph["source_context"], "View source context", "key-context")
            if glyph.get("raw_file"):
                context += _link(glyph["raw_file"], "Native crop", "key-context")
        search_text = " ".join([label, entry["value"], note, uncertain.get("status", "")]).lower()
        key_html.append(
            f'<tr id="{key_ids[label]}" data-key-entry="yes" '
            f'data-search="{_escape(search_text)}" data-contextual="{"yes" if is_contextual else "no"}" '
            f'data-open="{"yes" if is_open else "no"}">'
            f'<td class="key-image">{image_cell}</td>'
            f'<td><code class="key-label">{_escape(label)}</code>{context}</td>'
            f'<td class="key-value">{_escape(_display_value(entry["value"]))}</td>'
            f'<td class="count-cell">{_escape(entry["occurrences"])}</td>'
            f'<td>{status}' + (f'<div class="key-note">{_escape(note)}</div>' if note else "") + '</td></tr>'
        )

    rows_html = []
    class_names = {
        "A": "A · comparatively supported",
        "B": "B · contextual",
        "C": "C · affected ink",
        "cleartext": "Visible cleartext",
    }
    for index, entry in enumerate(reading_rows, 1):
        row_number = _number(entry.get("row", index))
        row_units = sorted(units_by_row[row_number], key=lambda unit: _number(unit["token"]))
        tokens = []
        for unit in row_units:
            number = _number(unit["token"])
            source_id = f"r{row_number:02d}_t{number:02d}"
            label, value, evidence_class = unit["label"], unit["value"], unit["evidence_class"]
            crop_path = f"views/units/{source_id}.png"
            box = ", ".join(str(unit[name]) for name in ("left", "top", "right", "bottom"))
            tokens.append(
                f'<div class="token {_escape(evidence_class)}" id="{source_id}">'
                f'<span class="token-id">{source_id}</span>'
                f'<a class="token-image" href="{crop_path}" title="Native crop; box {_escape(box)}">'
                f'<img src="{crop_path}" alt="{source_id}: {_escape(label)}" loading="lazy"></a>'
                f'<a class="token-label" href="#{key_ids[label]}">{_escape(label)}</a>'
                f'<span class="token-value">{_escape(_display_value(value))}</span>'
                f'<span class="token-grade">{_escape(class_names.get(evidence_class, evidence_class))}</span></div>'
            )
        note = f'<p class="row-note">{_escape(entry["note"])}</p>' if entry.get("note") else ""
        open_attribute = " open" if index == 1 else ""
        rows_html.append(
            f'<details id="row-{row_number:02d}"{open_attribute}>'
            '<summary><span class="row-summary">'
            f'<span>Row {row_number:02d}</span><small>{len(row_units)} units · image, literal and reading</small>'
            '</span></summary><div class="row-body">'
            f'<a href="views/rows/r{row_number:02d}.png" class="row-crop">'
            f'<img src="views/rows/r{row_number:02d}.png" alt="Source plate crop of cipher row {row_number}" loading="lazy"></a>'
            '<div class="field-label">Editorial French</div>'
            f'<p class="row-reading" lang="fr">{_escape(entry["text"])}</p>'
            '<div class="field-label">Literal output of transcription + proposed key</div>'
            f'<pre class="literal">{_escape(literal[index - 1])}</pre>{note}'
            '<details class="tokens"><summary>Inspect every transcribed unit in this row</summary>'
            f'<div class="token-grid">{"".join(tokens)}</div>'
            '<p class="legend">Each tile opens its native crop; its label links to the key. '
            'A and B describe the support for the proposed interpretation; C marks affected ink. '
            'These are evidence categories, not measured confidence scores.</p></details></div></details>'
        )

    alternative_html = []
    for item, choices in alternatives:
        choice_text = "; ".join(_display_value(str(choice)) for choice in choices)
        alternative_html.append(
            f'<tr><td>{_link("#" + key_ids[item["label"]], item["label"])}</td>'
            f'<td class="key-value">{_escape(_display_value(item["value"]))}</td>'
            f'<td>{_escape(choice_text)}</td>'
            f'<td class="uncertainty-note">{_escape(item.get("note", ""))}</td></tr>'
        )

    files = [
        ("METHODS.md", "How the solution is represented, rebuilt and checked."),
        ("SOURCES.md", "Source citations, attribution and image-use context."),
        ("CREDITS.md", "Research credit and acknowledged AI assistance."),
        ("sources/cipher_plate.png", "Source plate used for every coordinate and cipher crop."),
        ("inputs/transcription.txt", "The ordered labels for all transcribed cipher rows."),
        ("inputs/key.tsv", "Every proposed symbol value, including empty and unresolved values."),
        ("inputs/units.tsv", "Every transcribed unit with its value, evidence category and source coordinates."),
        ("inputs/uncertainties.tsv", "Contextual assignments, alternatives and interpretation notes."),
        ("inputs/defects.json", "Affected source-image locations and defect annotations."),
        ("inputs/editorial_interventions.tsv", "Character-level changes between literal output and editorial reading."),
        ("inputs/published_key_comparison.tsv", "Reported agreements with a modern published partial table, with evidence limits."),
        ("inputs/historical_comparison.tsv", "Historical comparison evidence and its limits."),
        ("inputs/reading_rows.json", "The French reading and its intervention notes, row by row."),
        ("inputs/reading.json", "The full French reading, English rendering and introductory notes."),
        ("solution/literal.txt", "Deterministic output from applying the supplied key to the transcription."),
        ("solution/reading.md", "The reading as a portable text document."),
        ("solution/reading_alignment.tsv", "A table connecting the literal output and editorial reading."),
        ("glyphs/glyphs.tsv", "Each cipher label's selected sample, output paths and occurrence count."),
        ("inputs/glyph_selection.json", "Selected glyph occurrences and source-coordinate instructions."),
        ("inputs/glyph_sheet_placements.json", "Placement data for rebuilding the glyph contact sheet."),
        ("glyphs/key_glyphs_sheet.png", "Contact sheet showing all selected cipher glyphs."),
    ]
    files_html = "".join(
        f'<tr><td>{_link(path, path)}</td><td>{_escape(description)}</td></tr>'
        for path, description in files
    )
    document = f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="The proposed Marmont decipherment: source image, French and English readings, symbol key, native crops, and reproducible verification.">
<meta name="author" content="Carter Church">
<title>The letter to Marmont — solution and evidence</title>
<style>{_STYLE}</style>
</head>
<body>
<a class="skip" href="#reading">Skip to the reading</a>
<header class="masthead"><div class="wrap"><span class="eyebrow">Marmont · March 1809</span><span class="edition">Solution &amp; evidence · v1.0.0</span></div></header>
<div class="wrap">
<div class="hero">
<div><h1>The letter<br>to Marmont</h1><p class="deck">A proposed decipherment, with the material to inspect and reproduce it.</p>
<p class="credit">Research and decipherment: <strong>Carter Church</strong><br>AI assistance: GPT-6 Astra and Claude</p>
<div class="counts"><div><b>{len(reading_rows)}</b><span>cipher rows</span></div><div><b>{len(units):,}</b><span>transcribed units</span></div><div><b>{cipher_count}</b><span>cipher labels</span></div></div>
</div>
<figure><a href="sources/cipher_plate.png"><img src="sources/cipher_plate.png" alt="The source cipher plate" width="1051" height="1246"></a><figcaption>Open the full source plate. All cipher crops below come from this image.</figcaption></figure>
</div>
<nav aria-label="Page sections"><a href="#reading">Read the letter</a><a href="#rows">Inspect the rows</a><a href="#key">Search the key</a><a href="#uncertainty">Open questions</a><a href="#reproduce">Reproduce &amp; verify</a><a href="#files">Data files</a></nav>
<main>
<section id="reading">
<h2>The reading</h2>
<p class="section-intro">The French is an editorial reading of the proposed key output. The English renders that reading. Native images, literal output and intervention notes remain available for direct comparison.</p>
<div class="note">{_paragraphs(reading.get("introduction"))}</div>
<div class="reading-grid"><article lang="fr" aria-labelledby="french-title"><h3 id="french-title" class="language">French · editorial reading</h3>{_paragraphs(reading["french_paragraphs"])}</article>
<article aria-labelledby="english-title"><h3 id="english-title" class="language">English · translation of the reading</h3>{_paragraphs(reading["english_paragraphs"])}</article></div>
<div class="reading-notes">{_paragraphs(reading.get("translation_note"))}</div>
<div class="file-links"><a href="solution/reading.md">Open the complete reading as text</a><a href="solution/literal.txt">Open the unedited literal output</a><a href="solution/reading_alignment.tsv">Open the row alignment</a></div>
</section>
<section id="rows"><h2>Inspect the {len(reading_rows)} rows</h2>
<p class="section-intro">Open a row to compare the source crop, editorial French and literal output. Expand its unit sequence to trace any value back to the actual mark and the proposed key.</p>
<div class="row-list">{"".join(rows_html)}</div>
</section>
<section id="key"><h2>The proposed key</h2>
<p class="section-intro">{cipher_count} cipher labels and {clear_count} labels for visible cleartext. A sample image identifies each cipher label; the raw files retain the selected source unit and its location. Empty output is displayed as ∅.</p>
<details id="key-panel"><summary>Open and search all {len(key)} key entries</summary>
<div class="toolbar"><div class="search-field"><label for="key-search">Search label, value or note</label><input id="key-search" type="search" placeholder="Try TARGET, GENERAL or a symbol label" autocomplete="off"></div>
<div><label for="key-scope">Show</label><select id="key-scope"><option value="all">All entries</option><option value="contextual">Contextual assignments</option><option value="open">Open alternatives / unresolved</option></select></div>
<p id="key-count" class="table-count" aria-live="polite">{len(key)} of {len(key)} entries</p></div>
<noscript><p class="noscript">The full key is shown below. Filtering requires JavaScript; all files and images work without it.</p></noscript>
<div class="table-scroll"><table class="key-table"><thead><tr><th scope="col">Glyph</th><th scope="col">Label &amp; source</th><th scope="col">Output</th><th scope="col">Count</th><th scope="col">Interpretation</th></tr></thead><tbody>{"".join(key_html)}</tbody></table></div></details>
<div class="file-links"><a href="inputs/key.tsv">Full key TSV</a><a href="glyphs/glyphs.tsv">Glyph sample index</a><a href="inputs/units.tsv">Unit and coordinate ledger</a></div>
</section>
<section id="uncertainty"><h2>Open questions</h2>
<p class="section-intro">{contextual_count} labels occur in the contextual evidence category. TARGET remains unresolved; its honorific in the reading is a contextual expansion. The table below records explicit alternatives. Additional contextual and empty-output assignments are available in the searchable key and uncertainty ledger.</p>
<div class="table-scroll"><table class="uncertainty-table"><thead><tr><th scope="col">Label</th><th scope="col">Current literal output</th><th scope="col">Alternatives</th><th scope="col">Note</th></tr></thead><tbody>{"".join(alternative_html)}</tbody></table></div>
<div class="file-links"><a href="inputs/uncertainties.tsv">Complete uncertainty ledger</a><a href="inputs/reading_rows.json">Editorial interventions by row</a></div>
</section>
<section id="reproduce"><h2>Reproduce and verify</h2>
<p class="section-intro">Run these commands from the extracted solution package. Verification checks agreement among the supplied transcription, key, outputs and image derivatives. Reproduction rebuilds those outputs from the included inputs.</p>
<div class="reproduce-grid"><div class="command-card"><h3>1. Verify the package</h3><p>Install the image dependency, then run the complete verification.</p><pre>python -m pip install -r requirements.txt\npython verify.py</pre></div>
<div class="command-card"><h3>2. Rebuild the solution</h3><p>Create a fresh set of outputs and this reader under <code>results/reproduced/</code>.</p><pre>python reproduce.py</pre></div></div>
<div class="note"><p>These checks establish reproducibility of the supplied solution. They do not independently authenticate every proposed symbol value, historical assertion or editorial restoration.</p></div>
<p class="path quiet">For text checks without the image dependency: <code>python verify.py --text-only</code>. To rebuild only the text outputs: <code>python reproduce.py --text-only</code>.</p>
</section>
<section id="files"><h2>Source and solution files</h2>
<p class="section-intro">Every link on this page opens an included file. The reader uses no external scripts, fonts, analytics or network services.</p>
<div class="table-scroll"><table class="files"><thead><tr><th scope="col">File</th><th scope="col">Purpose</th></tr></thead><tbody>{files_html}</tbody></table></div>
<div class="source-card"><a href="sources/napoleon_page_358.jpg"><img src="sources/napoleon_page_358.jpg" alt="Page 358 from the printed correspondence" loading="lazy"></a><div><h3>Printed correspondence reference</h3><p>The accompanying page is provided as a historical comparison source. Keep its printed text distinct from the cipher plate and the proposed reading.</p><a href="sources/napoleon_page_358.jpg">Open the reference page</a></div></div>
</section>
</main>
<footer>Research and decipherment: Carter Church. AI assistance: GPT-6 Astra and Claude. This reader is generated from the included solution data.</footer>
</div>
<script>{_SCRIPT}</script>
</body>
</html>
'''
    out.mkdir(parents=True, exist_ok=True)
    (out / "START_HERE.html").write_text(document, encoding="utf-8", newline="\n")
    links = _Links()
    links.feed(document)
    return {
        "artifact_count": 1,
        "artifacts": ["START_HERE.html"],
        "local_links": sorted(links.paths),
        "row_count": len(reading_rows),
        "unit_count": len(units),
        "key_entry_count": len(key),
        "contextual_label_count": contextual_count,
    }
