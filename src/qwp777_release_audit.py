"""Unified QWP-777 release audit: tests, regression, API, signatures, and report comparison."""
from __future__ import annotations
import argparse, hashlib, importlib.util, io, json, os, sys, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from qwp777_version import __version__, API_VERSION
from qwp777_profile import profile_circuit
from qwp777_memory import estimate_tableau_memory
from qwp777_benchmark import run_scaling_benchmark
from qwp777_soak import run_soak
from qwp777_stability_analyze import analyze_soak_report
from qwp777_device_compare import compare_soak_reports
from qwp777_release_series import build_release_series
from qwp777_runtime_info import collect_runtime_info
from qwp777_release_package import create_manifest, verify_manifest, ReleasePackageError
from qwp777_release_signing import sign_manifest, verify_manifest_signature, ReleaseSignatureError
from qwp777_provenance import create_provenance, verify_provenance, ProvenanceError
from qwp777_sbom import create_sbom, verify_sbom, SbomError
from qwp777_dependency_audit import audit_dependencies, DependencyAuditError
from qwp777_ed25519 import generate_key_pair
from qwp777_api_compat import check_api_compatibility
from qwp777_regression import run_regression_suite
from qwp777_release_compare import compare_release_reports
from qwp777_archive import create_report_archive, verify_report_archive, ArchiveError
from qwp777_ed25519 import generate_key_pair, Ed25519Error

class ReleaseAuditError(ValueError):
    pass

def summarize_check_status(checks):
    """Return a simple release-gate summary from named boolean checks."""
    failed = sorted(name for name, value in checks.items() if value is not True)
    return {"passed": not failed, "checks_total": len(checks),
            "checks_passed": len(checks)-len(failed), "checks_failed": len(failed),
            "failed_checks": failed}

def _run_unit_tests(project_root):
    tests_path = project_root / "tests"
    source_path = str(project_root / "src")
    if source_path in sys.path:
        sys.path.remove(source_path)
    sys.path.insert(0, source_path)
    suite = unittest.defaultTestLoader.discover(str(tests_path))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=1).run(suite)
    return {
        "passed": result.wasSuccessful(),
        "tests_run": result.testsRun,
        "failures": len(result.failures),
        "errors": len(result.errors),
        "failure_details": [str(item[0]) + ": " + item[1].splitlines()[-1] for item in result.failures],
        "error_details": [str(item[0]) + ": " + item[1].splitlines()[-1] for item in result.errors],
        "output_tail": stream.getvalue()[-2000:]
    }

def _signature_self_test(project_root):
    """Exercise HMAC unconditionally and Ed25519 if its optional dependency exists."""
    root = project_root
    result = {"hmac_sha256": {"status": "failed"}, "ed25519": {"status": "not_run"}}
    with tempfile.TemporaryDirectory(prefix="qwp777-audit-") as tmp:
        tmp_path = Path(tmp)
        report_path = tmp_path / "report.json"
        config_path = tmp_path / "configuration.json"
        report_path.write_text(json.dumps({"report_schema": "qwp777-release-audit-signature-test-1"}) + "\n")
        config_path.write_text(json.dumps({"num_qubits": 1, "gates": [{"gate":"MEASURE","qubits":[0]}]}) + "\n")
        hmac_secret = "qwp777-ephemeral-audit-secret-never-shipped"
        try:
            hmac_archive = create_report_archive(
                report_path, config_path, tmp_path/"hmac", "hmac-self-test",
                signing_key=hmac_secret, require_signature=True)
            verification = verify_report_archive(hmac_archive["zip_path"], signing_key=hmac_secret)
            result["hmac_sha256"] = {
                "status": "passed" if verification.get("verified") else "failed",
                "verification": verification.get("verified", False)
            }
        except Exception as exc:
            result["hmac_sha256"] = {"status": "failed", "error": str(exc)}
        if importlib.util.find_spec("cryptography") is None:
            result["ed25519"] = {"status": "optional_dependency_unavailable"}
        else:
            private_path = tmp_path/"private.pem"
            public_path = tmp_path/"public.pem"
            try:
                generate_key_pair(private_path, public_path, passphrase="ephemeral-audit-passphrase")
                signed = create_report_archive(
                    report_path, config_path, tmp_path/"ed25519", "ed25519-self-test",
                    require_signature=True, ed25519_private_key_path=private_path,
                    private_key_password="ephemeral-audit-passphrase")
                checked = verify_report_archive(signed["zip_path"], public_key_path=public_path)
                result["ed25519"] = {
                    "status": "passed" if checked.get("verified") else "failed",
                    "verification": checked.get("verified", False),
                    "algorithm": checked.get("signature_algorithm")
                }
            except Exception as exc:
                result["ed25519"] = {"status": "failed", "error": str(exc)}
    return result

def run_release_audit(project_root=None, previous_report_path=None,
                      archive_path=None, public_key_path=None,
                      hmac_key_env="QWP777_ARCHIVE_HMAC_KEY",
                      run_tests=True):
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[1]
    api = check_api_compatibility(root/"compatibility"/"api-v1.6.0.json")
    api["contract"]["path"] = "compatibility/api-v1.6.0.json"
    current_contract_name = f"api-v{__version__}.json"
    current_api = check_api_compatibility(root/"compatibility"/current_contract_name)
    current_api["contract"]["path"] = f"compatibility/{current_contract_name}"
    current_api_contract_ok = (
        current_api.get("compatible") is True
        and current_api.get("current", {}).get("release") == __version__
        and current_api.get("current", {}).get("api_version") == API_VERSION
        and current_api.get("contract", {}).get("snapshot_release") == __version__
        and current_api.get("contract", {}).get("snapshot_api_version") == API_VERSION
    )
    previous_baseline = root/"regression"/"baselines"/"v1.5.0.json"
    current_baseline = root/"regression"/"baselines"/f"v{__version__}.json"
    if not current_baseline.exists():
        raise ReleaseAuditError(f"current version baseline missing: {current_baseline}")
    previous_regression = run_regression_suite(previous_baseline)
    current_regression = run_regression_suite(current_baseline)
    baseline_hash = hashlib.sha256(current_baseline.read_bytes()).hexdigest()
    sidecar_path = Path(str(current_baseline)+".sha256")
    sidecar_valid = sidecar_path.exists() and sidecar_path.read_text(encoding="utf-8").split()[0] == baseline_hash
    reference_report = Path(previous_report_path) if previous_report_path else root/"compatibility"/"reports"/"v2.9.0-regression.json"
    with tempfile.TemporaryDirectory(prefix="qwp777-release-compare-") as tmp:
        current_report_path = Path(tmp)/"current-regression.json"
        current_report_path.write_text(json.dumps(current_regression, indent=2, ensure_ascii=False)+"\n")
        release_comparison = compare_release_reports(reference_report, current_report_path)
    try:
        release_comparison["previous_report"] = str(reference_report.resolve().relative_to(root.resolve()))
    except ValueError:
        release_comparison["previous_report"] = reference_report.name
    release_comparison["current_report"] = f"generated in-memory from the v{__version__} regression baseline"
    series_smoke = {"passed": False}
    try:
        with tempfile.TemporaryDirectory(prefix="qwp777-release-series-") as tmp:
            current_series_report = Path(tmp) / "current-regression.json"
            current_series_report.write_text(json.dumps(current_regression, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            series = build_release_series([reference_report, current_series_report])
        series_smoke = {
            "passed": (series.get("report_schema") == "qwp777-release-series-report-1"
                       and series.get("summary", {}).get("releases_total") == 2
                       and series.get("summary", {}).get("release_transitions_compared") == 1
                       and series.get("summary", {}).get("cross_release_regression_failures") == 0),
            "releases_total": series.get("summary", {}).get("releases_total"),
            "release_transitions_compared": series.get("summary", {}).get("release_transitions_compared"),
            "cross_release_regression_failures": series.get("summary", {}).get("cross_release_regression_failures")
        }
    except Exception as exc:
        series_smoke = {"passed": False, "error": str(exc)}
    signatures = _signature_self_test(root)
    profile_smoke = {"passed": False, "runtime": collect_runtime_info()}
    try:
        smoke = profile_circuit({
            "num_qubits": 1,
            "gates": [{"gate": "MEASURE", "qubits": [0]}],
            "shots": 3,
            "seed": 13
        }, repeats=1)
        profile_smoke = {
            "passed": (smoke.get("report_schema") == "qwp777-profile-report-1"
                       and len(smoke.get("timing_seconds", {}).get("samples", [])) == 1
                       and smoke.get("timing_seconds", {}).get("minimum", -1) >= 0
                       and smoke.get("python_tracemalloc_peak_bytes", {}).get("maximum", -1) >= 0),
            "timing_seconds": smoke.get("timing_seconds"),
            "python_tracemalloc_peak_bytes": smoke.get("python_tracemalloc_peak_bytes"),
            "runtime": smoke.get("runtime")
        }
    except Exception as exc:
        profile_smoke = {"passed": False, "error": str(exc), "runtime": collect_runtime_info()}
    memory_estimate = {"passed": False}
    try:
        mem1 = estimate_tableau_memory(1)
        mem8 = estimate_tableau_memory(8)
        memory_estimate = {
            "passed": mem1["estimated_list_container_bytes"] > 0
                      and mem8["estimated_list_container_bytes"] > mem1["estimated_list_container_bytes"]
                      and mem8["matrix_slots_total"] == 4 * 8 * 8,
            "one_qubit_list_container_bytes": mem1["estimated_list_container_bytes"],
            "eight_qubit_list_container_bytes": mem8["estimated_list_container_bytes"]
        }
    except Exception as exc:
        memory_estimate = {"passed": False, "error": str(exc)}
    benchmark_smoke = {"passed": False}
    try:
        bench = run_scaling_benchmark(qubit_sizes=(1, 2), shot_sizes=(1,), repeats=1,
                                      seed=19, max_work_units=100000)
        benchmark_smoke = {
            "passed": bench.get("summary", {}).get("cases_total") == 2
                      and bench.get("summary", {}).get("cases_failed") == 0,
            "summary": bench.get("summary"),
            "planned_work_units": bench.get("configuration", {}).get("planned_work_units")
        }
    except Exception as exc:
        benchmark_smoke = {"passed": False, "error": str(exc)}
    soak_smoke = {"passed": False}
    try:
        soak = run_soak({"num_qubits": 1, "gates": [{"gate": "MEASURE", "qubits": [0]}],
                         "shots": 2, "seed": 23}, iterations=6, warmup=0, max_work_units=10000)
        soak_smoke = {
            "passed": (soak.get("report_schema") == "qwp777-soak-report-1"
                       and soak.get("summary", {}).get("iterations_completed") == 6
                       and soak.get("summary", {}).get("all_count_totals_valid") is True
                       and len(soak.get("samples", [])) == 6),
            "rss_available": soak.get("summary", {}).get("rss_current_bytes", {}).get("available"),
            "tracemalloc_peak_bytes": soak.get("summary", {}).get("python_tracemalloc_peak_bytes_overall")
        }
    except Exception as exc:
        soak_smoke = {"passed": False, "error": str(exc)}
    stability_analysis_smoke = {"passed": False}
    try:
        analysis = analyze_soak_report(soak, min_samples=5)
        stability_analysis_smoke = {
            "passed": analysis.get("report_schema") == "qwp777-stability-analysis-1"
                      and analysis.get("input", {}).get("samples_total") == 6
                      and analysis.get("summary", {}).get("status") in {
                          "no_suspicious_growth", "anomaly_candidate"},
            "status": analysis.get("summary", {}).get("status"),
            "findings_total": analysis.get("summary", {}).get("findings_total")
        }
    except Exception as exc:
        stability_analysis_smoke = {"passed": False, "error": str(exc)}
    device_compare_smoke = {"passed": False}
    try:
        comparison = compare_soak_reports(soak, soak)
        device_compare_smoke = {
            "passed": comparison.get("report_schema") == "qwp777-device-comparison-1"
                      and comparison.get("summary", {}).get("workloads_match") is True
                      and comparison.get("summary", {}).get("cross_host_comparison") is False
                      and comparison.get("median_duration_seconds", {}).get("change_percent") == 0.0
                      and comparison.get("median_python_tracemalloc_current_bytes_after_cleanup", {}).get("change_percent") == 0.0,
            "workloads_match": comparison.get("summary", {}).get("workloads_match"),
            "same_host_fingerprint": comparison.get("environment", {}).get("same_host_fingerprint")
        }
    except Exception as exc:
        device_compare_smoke = {"passed": False, "error": str(exc)}
    external_signature = {"status": "not_requested"}
    if archive_path:
        try:
            if public_key_path:
                checked = verify_report_archive(archive_path, public_key_path=public_key_path)
            else:
                secret = os.environ.get(hmac_key_env)
                if not secret:
                    raise ReleaseAuditError(f"environment variable {hmac_key_env} is not set and no public key was given")
                checked = verify_report_archive(archive_path, signing_key=secret)
            external_signature = {"status": "passed" if checked.get("verified") else "failed",
                                  "algorithm": checked.get("signature_algorithm"),
                                  "archive_name": checked.get("archive_name")}
        except Exception as exc:
            external_signature = {"status": "failed", "error": str(exc)}
    manifest_smoke = {"passed": False}
    try:
        with tempfile.TemporaryDirectory(prefix="qwp777-release-manifest-") as tmp:
            sample_root = Path(tmp) / "sample-release"
            (sample_root / "docs").mkdir(parents=True)
            (sample_root / "VERSION").write_text(__version__ + "\n", encoding="utf-8")
            (sample_root / "README.md").write_text("manifest smoke test\n", encoding="utf-8")
            created = create_manifest(sample_root)
            clean = verify_manifest(sample_root)
            (sample_root / "README.md").write_text("tampered\n", encoding="utf-8")
            tampered = verify_manifest(sample_root)
            manifest_smoke = {
                "passed": (created.get("manifest_schema") == "qwp777-release-manifest-1"
                           and clean.get("verified") is True
                           and tampered.get("verified") is False
                           and "README.md" in tampered.get("hash_or_size_mismatches", [])),
                "files_total": created.get("files_total"),
                "tamper_detected": tampered.get("verified") is False
            }
    except Exception as exc:
        manifest_smoke = {"passed": False, "error": str(exc)}

    manifest_signature_smoke = {"status": "failed"}
    try:
        if importlib.util.find_spec("cryptography") is None:
            manifest_signature_smoke = {"status": "optional_dependency_unavailable"}
        else:
            with tempfile.TemporaryDirectory(prefix="qwp777-manifest-signature-") as tmp:
                sample_root = Path(tmp) / "release"
                (sample_root / "docs").mkdir(parents=True)
                (sample_root / "VERSION").write_text(__version__ + "\n", encoding="utf-8")
                (sample_root / "README.md").write_text("signature smoke test\n", encoding="utf-8")
                manifest_path = sample_root / "docs" / "RELEASE_MANIFEST.json"
                create_manifest(sample_root)
                private_path, public_path = Path(tmp)/"private.pem", Path(tmp)/"public.pem"
                generate_key_pair(private_path, public_path)
                signature_path = Path(tmp)/"manifest.sig.json"
                sign_manifest(manifest_path, private_path, signature_path)
                verified_sig = verify_manifest_signature(manifest_path, signature_path, public_path)
                manifest_path.write_text(manifest_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
                try:
                    verify_manifest_signature(manifest_path, signature_path, public_path)
                    tamper_rejected = False
                except ReleaseSignatureError:
                    tamper_rejected = True
                manifest_signature_smoke = {"status": "passed" if verified_sig.get("verified") and tamper_rejected else "failed",
                                             "roundtrip_verified": verified_sig.get("verified"),
                                             "tampered_manifest_rejected": tamper_rejected}
    except Exception as exc:
        manifest_signature_smoke = {"status": "failed", "error": str(exc)}

    provenance_smoke = {"passed": False}
    try:
        with tempfile.TemporaryDirectory(prefix="qwp777-provenance-") as tmp:
            sample_root = Path(tmp) / "release"
            for folder in ("docs", "compatibility", "regression/baselines"):
                (sample_root/folder).mkdir(parents=True, exist_ok=True)
            (sample_root/"VERSION").write_text(__version__ + "\n", encoding="utf-8")
            (sample_root/"compatibility"/f"api-v{__version__}.json").write_text("{}\n", encoding="utf-8")
            (sample_root/"regression"/"baselines"/f"v{__version__}.json").write_text("{}\n", encoding="utf-8")
            (sample_root/"docs"/"RELEASE_AUDIT.json").write_text(json.dumps({"summary":{"passed":True,"checks_passed":1,"checks_total":1},"unit_tests":{"tests_run":1}}), encoding="utf-8")
            (sample_root/"docs"/"TEST_REPORT.json").write_text(json.dumps({"report_schema":"smoke-test-report-1"}), encoding="utf-8")
            created = create_provenance(sample_root, source_release="2.7.0")
            clean = verify_provenance(sample_root)
            (sample_root/"docs"/"TEST_REPORT.json").write_text("tampered\n", encoding="utf-8")
            tampered = verify_provenance(sample_root)
            provenance_smoke = {"passed": created.get("provenance_schema") == "qwp777-build-provenance-1"
                                and clean.get("verified") is True and tampered.get("verified") is False,
                                "inputs_checked": clean.get("inputs_checked"),
                                "tamper_detected": tampered.get("verified") is False}
    except Exception as exc:
        provenance_smoke = {"passed": False, "error": str(exc)}

    sbom_smoke = {"passed": False}
    try:
        sbom_result = verify_sbom(root, "docs/SBOM.cdx.json", "DEPENDENCIES.json")
        sbom_smoke = {"passed": sbom_result.get("verified") is True,
                      "verification": sbom_result}
    except Exception as exc:
        sbom_smoke = {"passed": False, "error": str(exc)}

    dependency_audit_smoke = {"passed": False}
    try:
        dep_report = audit_dependencies(root, "docs/SBOM.cdx.json", "DEPENDENCIES.json")
        dependency_audit_smoke = {
            "passed": dep_report.get("summary", {}).get("passed") is True,
            "summary": dep_report.get("summary"),
            "vulnerability_status": dep_report.get("security_assessment", {}).get("vulnerability_status"),
            "live_vulnerability_database_used": dep_report.get("security_assessment", {}).get("live_vulnerability_database_used")
        }
    except Exception as exc:
        dependency_audit_smoke = {"passed": False, "error": str(exc)}

    unit_tests = _run_unit_tests(root) if run_tests else {"passed": False, "tests_run": 0,
                                                           "failures": 0, "errors": 0,
                                                           "note": "unit test run disabled"}
    checks = {
        "unit_tests": unit_tests["passed"],
        "api_compatibility": api.get("compatible") is True,
        "current_api_contract": current_api_contract_ok,
        "previous_regression_baseline": previous_regression.get("summary", {}).get("passed") is True,
        "current_regression_baseline": current_regression.get("summary", {}).get("passed") is True,
        "current_baseline_checksum": sidecar_valid,
        "release_comparison_clean": release_comparison.get("summary", {}).get("clean") is True,
        "hmac_signature_roundtrip": signatures["hmac_sha256"].get("status") == "passed",
        "ed25519_signature_roundtrip": signatures["ed25519"].get("status") in {"passed", "optional_dependency_unavailable"},
        "profile_runtime_smoke_test": profile_smoke.get("passed") is True,
        "memory_estimator_sanity": memory_estimate.get("passed") is True,
        "scaling_benchmark_smoke_test": benchmark_smoke.get("passed") is True,
        "soak_stability_smoke_test": soak_smoke.get("passed") is True,
        "stability_anomaly_analysis_smoke_test": stability_analysis_smoke.get("passed") is True,
        "cross_device_comparison_smoke_test": device_compare_smoke.get("passed") is True,
        "multi_release_series_smoke_test": series_smoke.get("passed") is True,
        "release_manifest_smoke_test": manifest_smoke.get("passed") is True,
        "release_manifest_signature_roundtrip": manifest_signature_smoke.get("status") in {"passed", "optional_dependency_unavailable"},
        "build_provenance_integrity_smoke_test": provenance_smoke.get("passed") is True,
        "cyclonedx_sbom_integrity_smoke_test": sbom_smoke.get("passed") is True,
        "offline_dependency_audit_smoke_test": dependency_audit_smoke.get("passed") is True,
    }
    if archive_path:
        checks["external_archive_signature"] = external_signature.get("status") == "passed"
    summary = summarize_check_status(checks)
    return {
        "report_schema": "qwp777-release-audit-report-1",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "software": {"release": __version__, "api_version": API_VERSION},
        "summary": summary,
        "checks": checks,
        "unit_tests": unit_tests,
        "api_compatibility": api,
        "current_api_contract": current_api,
        "regression": {
            "previous_baseline": {
                "path": "regression/baselines/v1.5.0.json",
                "sha256": hashlib.sha256(previous_baseline.read_bytes()).hexdigest(),
                "summary": previous_regression["summary"]
            },
            "current_baseline": {
                "path": f"regression/baselines/v{__version__}.json",
                "sha256": baseline_hash,
                "checksum_sidecar_valid": sidecar_valid,
                "summary": current_regression["summary"]
            }
        },
        "release_comparison": release_comparison,
        "profile_runtime_smoke_test": profile_smoke,
        "memory_estimator_smoke_test": memory_estimate,
        "scaling_benchmark_smoke_test": benchmark_smoke,
        "soak_stability_smoke_test": soak_smoke,
        "stability_anomaly_analysis_smoke_test": stability_analysis_smoke,
        "cross_device_comparison_smoke_test": device_compare_smoke,
        "multi_release_series_smoke_test": series_smoke,
        "release_manifest_smoke_test": manifest_smoke,
        "release_manifest_signature_smoke_test": manifest_signature_smoke,
        "build_provenance_integrity_smoke_test": provenance_smoke,
        "cyclonedx_sbom_smoke_test": sbom_smoke,
        "offline_dependency_audit_smoke_test": dependency_audit_smoke,
        "signature_verification": {
            "self_test": signatures,
            "external_archive": external_signature
        },
        "caveats": [
            "Release audit combines finite tests and declared contracts; it is not formal verification.",
            "Cryptographic signatures authenticate artifacts for the configured trust model, not scientific validity.",
            "The optional Qiskit Aer backend is not part of this audit unless separately invoked.",
            "QWP-777 is software prototype code, not physical quantum hardware."
        ]
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a unified QWP-777 release audit report.")
    parser.add_argument("-o", "--output", help="write full release audit JSON to this path")
    parser.add_argument("--previous-report", help="optional prior release regression report JSON")
    parser.add_argument("--verify-archive", help="optional existing signed report archive ZIP to verify")
    parser.add_argument("--public-key", help="Ed25519 public key PEM for --verify-archive")
    parser.add_argument("--hmac-key-env", default="QWP777_ARCHIVE_HMAC_KEY",
                        help="environment variable containing HMAC secret")
    parser.add_argument("--skip-unit-tests", action="store_true", help="skip running the unit test suite")
    args = parser.parse_args(argv)
    try:
        report = run_release_audit(
            previous_report_path=args.previous_report,
            archive_path=args.verify_archive,
            public_key_path=args.public_key,
            hmac_key_env=args.hmac_key_env,
            run_tests=not args.skip_unit_tests
        )
        rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            Path(args.output).write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
        return 0 if report["summary"]["passed"] else 1
    except Exception as exc:
        print(f"qwp777-release-audit: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
