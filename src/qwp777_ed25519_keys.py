"""Generate an Ed25519 key pair for QWP-777 report archives."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from qwp777_ed25519 import generate_key_pair, Ed25519Error

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate an Ed25519 PEM key pair. Never publish the private key.")
    parser.add_argument("--private-key", required=True, help="path for private key PEM (never share this file)")
    parser.add_argument("--public-key", required=True, help="path for public key PEM")
    parser.add_argument("--passphrase-env", help="optional environment variable holding a private-key passphrase")
    parser.add_argument("-o", "--output", help="write key-generation summary JSON to this path")
    args = parser.parse_args(argv)
    try:
        passphrase = os.environ.get(args.passphrase_env) if args.passphrase_env else None
        if args.passphrase_env and not passphrase:
            raise Ed25519Error(f"passphrase environment variable {args.passphrase_env} is empty or missing")
        report = generate_key_pair(args.private_key, args.public_key, passphrase)
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0
    except (OSError, Ed25519Error) as exc:
        print(f"qwp777-ed25519-keys: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
