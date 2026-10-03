#!/usr/bin/env python3
"""Reproduce the supplied final solution locally, without network access."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

sys.dont_write_bytecode = True
from scripts import core

ROOT = Path(__file__).resolve().parent


def summary(result: dict) -> dict:
    """Keep terminal reports compact when builders return file inventories."""
    compact = {key: value for key, value in result.items() if key not in {"files", "artifacts", "local_links"}}
    if "files" in result:
        compact["generated_files"] = len(result["files"])
    if "local_links" in result:
        compact["local_links"] = len(result["local_links"])
    return compact


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("results/reproduced"),
                        help="output directory below results/ (default: results/reproduced)")
    parser.add_argument("--text-only", action="store_true",
                        help="reproduce text using only the Python standard library; skip images and portal")
    args = parser.parse_args()
    try:
        out = core.safe_results_path(ROOT, args.out)
        if not args.text_only:
            from scripts import media, portal
        report = {"scope": "Reproduction from the supplied final transcription, proposed key and editorial inputs.",
                  "mode": "text-only" if args.text_only else "full", "checks": {}}
        report["checks"]["text"] = summary(core.build(ROOT, out))
        if not args.text_only:
            for name in ("inputs", "sources"):
                source = ROOT / name
                core.require(source.is_dir() and not source.is_symlink(), f"Missing or unsafe source directory: {name}")
                core.require(not any(file.is_symlink() for file in source.rglob("*")), f"Symlink in source directory: {name}")
                shutil.copytree(source, out / name, dirs_exist_ok=True)
            for name in ("METHODS.md", "SOURCES.md", "CREDITS.md"):
                source = ROOT / name
                core.require(source.is_file() and not source.is_symlink(), f"Missing or unsafe documentation: {name}")
                shutil.copyfile(source, out / name)
            report["checks"]["media"] = summary(media.build(ROOT, out))
            report["checks"]["portal"] = summary(portal.build(ROOT, out))
        report["checks"]["comparison"] = core.compare_generated(ROOT, out, images=not args.text_only)
        if not args.text_only:
            report["checks"]["offline_portal"] = core.verify_portal(out)
        report["status"] = "PASS_TEXT_ONLY" if args.text_only else "PASS"
        report["output"] = out.relative_to(ROOT).as_posix()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, ImportError, KeyError, IndexError, TypeError) as exc:
        report = {"status": "FAIL", "error": str(exc)}
        if isinstance(exc, ImportError):
            report["help"] = "Install requirements.txt for full reproduction, or use --text-only explicitly."
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
