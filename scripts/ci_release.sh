#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION")"
OUT="${1:-$ROOT/../dist-v${VERSION}}"
ZIP_PATH="$OUT/Qwantum-Processor-777-v${VERSION}.zip"
mkdir -p "$OUT"
cd "$ROOT"
export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

python -m compileall -q src tests
python -m unittest discover -s tests -v 2>&1 | tee "$OUT/unit-tests.log"
python src/qwp777_api_compat.py --contract "compatibility/api-v${VERSION}.json" -o "$OUT/api-compatibility.json"
python src/qwp777_regression.py --baseline "regression/baselines/v${VERSION}.json" -o "compatibility/reports/v${VERSION}-regression.json"
python src/qwp777_sbom.py generate --root . --output docs/SBOM.cdx.json
python src/qwp777_sbom.py verify --root . --sbom docs/SBOM.cdx.json
python src/qwp777_dependency_audit.py --root . --sbom docs/SBOM.cdx.json -o docs/DEPENDENCY_AUDIT.json
python src/qwp777_release_audit.py -o docs/RELEASE_AUDIT.json
python - "$OUT/unit-tests.log" <<'PY'
import json, re, sys, platform
from pathlib import Path
log = Path(sys.argv[1]).read_text(errors="replace")
m = re.search(r"Ran (\d+) tests? in ([0-9.]+)s", log)
failed = bool(re.search(r"\bFAILED\b|\bERROR\b", log))
if not m or failed:
    raise SystemExit("could not parse successful unittest summary")
root = Path.cwd()
version = (root / "VERSION").read_text().strip()
report = {
 "report_schema":"qwp777-test-report-1",
 "software":{"name":"QWP-777","release":version,"api_version":"3.0","result_schema":"qwp777-experiment-1"},
 "summary":{"tests_run":int(m.group(1)),"tests_passed":int(m.group(1)),"failures":0,"errors":0,"status":"passed"},
 "environment":{"python":platform.python_version(),"platform":platform.platform()},
 "validation_steps":["compileall","unittest","API compatibility","fixed-seed regression","CycloneDX SBOM","offline dependency audit","release audit","tag/version guard unit tests"],
 "limitations":["No online CVE/OSV/vendor-advisory database was queried.","GitHub Actions and Android/Termux require execution in their target environments."]
}
(root/"docs/TEST_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
(root/"docs/TEST_REPORT.md").write_text(f"# QWP-777 v{version} — Test report\n\n- Unit tests: {m.group(1)} passed.\n- API compatibility, regression, SBOM, dependency audit and release audit are pipeline gates.\n- Python: {platform.python_version()} on {platform.platform()}.\n- No live CVE/OSV database was queried; Android/Termux was not independently tested.\n")
PY
SOURCE_ARGS=(--source-release 3.0.0)
if [[ -f "$ROOT/../Qwantum-Processor-777-v3.0.0.zip" ]]; then
  SOURCE_ARGS+=(--source-archive "$ROOT/../Qwantum-Processor-777-v3.0.0.zip")
fi
python src/qwp777_provenance.py create --root . "${SOURCE_ARGS[@]}"
python src/qwp777_provenance.py verify --root .
python src/qwp777_release_package.py build --root . --zip-output "$ZIP_PATH"
python src/qwp777_release_package.py verify --root .
python src/qwp777_release_package.py verify-archive "$ZIP_PATH"
cp docs/RELEASE_MANIFEST.json "$OUT/RELEASE_MANIFEST.json"
cp docs/SBOM.cdx.json "$OUT/SBOM.cdx.json"
cp docs/DEPENDENCY_AUDIT.json "$OUT/DEPENDENCY_AUDIT.json"
cp docs/PROVENANCE.json "$OUT/PROVENANCE.json"
cp docs/RELEASE_AUDIT.json "$OUT/RELEASE_AUDIT.json"
cp docs/TEST_REPORT.md "$OUT/TEST_REPORT.md"
cp docs/TEST_REPORT.json "$OUT/TEST_REPORT.json"
cp "compatibility/reports/v${VERSION}-regression.json" "$OUT/regression-report.json"
echo "Release artifacts created in: $OUT"
