# Migration v2.6.0 → v2.7.0

No simulator API migration is required. Existing `qwp777_api` exports, callable signatures and the `qwp777-experiment-1` result schema are preserved.

The release workflow gains a packaging command:

```bash
python src/qwp777_release_package.py build \
  --root . \
  --zip-output ../Qwantum-Processor-777-v2.7.0.zip
python src/qwp777_release_package.py verify-archive \
  ../Qwantum-Processor-777-v2.7.0.zip
```

The ZIP output must be outside the release root. The tool creates `docs/RELEASE_MANIFEST.json` and the adjacent `.sha256` sidecar. The manifest does not hash itself; the detached ZIP checksum covers the complete archive. For publisher authentication, additionally use the existing HMAC/Ed25519 signed-archive workflows and verify with a trusted key.
