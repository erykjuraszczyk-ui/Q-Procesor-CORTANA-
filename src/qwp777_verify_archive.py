"""CLI to verify QWP-777 archives signed by HMAC-SHA256 or Ed25519."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from qwp777_archive import verify_report_archive, ArchiveError

def main(argv=None):
    parser = argparse.ArgumentParser(description="Verify archive ZIP integrity, content hashes, and its HMAC or Ed25519 signature.")
    parser.add_argument("archive", help="report archive ZIP")
    parser.add_argument("--key-env", default="QWP777_ARCHIVE_HMAC_KEY",
                        help="environment variable containing HMAC shared secret")
    parser.add_argument("--public-key", help="Ed25519 public key PEM; mutually exclusive with HMAC verification")
    parser.add_argument("-o", "--output", help="write verification report JSON to this path")
    args = parser.parse_args(argv)
    try:
        if args.public_key:
            report = verify_report_archive(args.archive, public_key_path=args.public_key)
        else:
            key = os.environ.get(args.key_env)
            if not key:
                raise ArchiveError(f"required HMAC secret is missing from environment variable {args.key_env}; or provide --public-key")
            report = verify_report_archive(args.archive, signing_key=key)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, ArchiveError) as exc:
        print(f"qwp777-verify-archive: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
