#!/usr/bin/env python3
"""Verify package integrity and reproduce the final solution offline.

The default checks text, source-derived image pixels and the offline portal.
PASS does not establish unique decipherment or manuscript authentication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
from scripts import core

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text-only", action="store_true",
                        help="check hashes and text using the standard library; explicitly skip image and portal checks")
    parser.add_argument("--out", type=Path,
                        help="also save this deterministic JSON report to a file below results/")
    args = parser.parse_args()
    destination = None
    report = {
        "scope": "Package integrity and internal reproducibility of the supplied final solution; "
                 "not proof of historical authenticity, unique decipherment, or independent rediscovery.",
        "mode": "text-only" if args.text_only else "full", "checks": {},
    }
    try:
        if args.out:
            destination = core.safe_results_path(ROOT, args.out, directory=False)
        report["checks"]["manifest"] = core.verify_manifest(ROOT)
        report["checks"]["text"] = core.verify(ROOT)
        if args.text_only:
            report["checks"]["images"] = {"status": "SKIPPED_EXPLICIT_TEXT_ONLY"}
            report["checks"]["portal"] = {"status": "SKIPPED_EXPLICIT_TEXT_ONLY"}
        else:
            from scripts import media
            image_report = media.verify(ROOT)
            core.require(image_report.get("pass") is True, "Image verification did not pass")
            report["checks"]["images"] = image_report
            report["checks"]["portal"] = core.verify_portal(ROOT)
        report["status"] = "PASS_TEXT_ONLY" if args.text_only else "PASS"
    except (OSError, ValueError, ImportError, KeyError, IndexError, TypeError) as exc:
        report["status"] = "FAIL"
        report["error"] = str(exc)
        if isinstance(exc, ImportError):
            report["help"] = "Install requirements.txt for full verification, or use --text-only explicitly."
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if destination is not None:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(payload, encoding="utf-8")
        except OSError as exc:
            report["status"] = "FAIL"
            report["error"] = f"Cannot write verification report: {exc}"
            payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    print(payload, end="")
    return 1 if report["status"] == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
