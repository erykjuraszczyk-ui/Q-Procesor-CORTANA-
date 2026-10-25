#!/usr/bin/env python3
"""Fail closed unless a release tag exactly matches the checked-out VERSION."""
from __future__ import annotations
import argparse
import re
import sys
from pathlib import Path

SEMVER = re.compile(r"0|[1-9][0-9]*")

def valid_version(value: str) -> bool:
    parts = value.split(".")
    return len(parts) == 3 and all(SEMVER.fullmatch(part) for part in parts)

def check_tag(tag: str, version: str) -> bool:
    return valid_version(version) and tag == f"v{version}"

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True, help="Git tag such as v3.1.0")
    parser.add_argument("--version-file", default=str(Path(__file__).resolve().parents[1] / "VERSION"))
    args = parser.parse_args(argv)
    try:
        version = Path(args.version_file).read_text(encoding="utf-8").strip()
    except OSError as exc:
        print(f"release-tag-check: cannot read version file: {exc}", file=sys.stderr)
        return 2
    if not check_tag(args.tag, version):
        print(f"release-tag-check: tag {args.tag!r} does not exactly match VERSION {version!r} (expected v{version})", file=sys.stderr)
        return 1
    print(f"release-tag-check: {args.tag} matches VERSION {version}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
