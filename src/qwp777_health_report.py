"""Build a consolidated QWP-777 health report from JSON diagnostics."""
from __future__ import annotations
import argparse, html, json, sys
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "qwp777-health-report-1"
class HealthReportError(ValueError):
    pass

def build_health_report(paths):
    items = []
    for value in paths:
        path = Path(value)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HealthReportError(f"cannot read {path}: {exc}") from exc
        if not isinstance(data, dict):
            raise HealthReportError(f"{path}: report root must be a JSON object")
        schema = data.get("report_schema", "unknown")
        summary = data.get("summary", {})
        status = summary.get("status") or summary.get("passed")
        if status is None:
            status = "informational"
        items.append({"file": path.name, "report_schema": schema, "status": status,
                      "software": data.get("software", {}), "summary": summary, "data": data})
    statuses = [str(x["status"]).lower() for x in items]
    warnings = sum(1 for x in statuses if x in {"false", "failed", "failure", "anomaly_candidate", "insufficient_data", "error"})
    return {"report_schema": SCHEMA, "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reports_total": len(items), "reports_with_warning_status": warnings,
            "overall_status": "review_required" if warnings else "informational_or_ok", "reports": items,
            "caveats": ["This summarizes supplied JSON reports; it does not rerun their tests.",
                        "Missing or unrecognized status fields are informational, not passed.",
                        "Memory metrics may represent tracemalloc allocations rather than total process RAM."]}

def render_html(report):
    rows = []
    for item in report["reports"]:
        rows.append("<tr><td>" + html.escape(item["file"]) + "</td><td>" +
                    html.escape(str(item["report_schema"])) + "</td><td>" +
                    html.escape(str(item["status"])) + "</td></tr>")
    caveats = "".join("<li>" + html.escape(x) + "</li>" for x in report["caveats"])
    head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>QWP-777 Health Report</title><style>'
            'body{font:16px system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#172033}'
            'table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd2dc;padding:.6rem;text-align:left}'
            'code{overflow-wrap:anywhere}</style></head><body><h1>QWP-777 Health Report</h1><p>Generated UTC: <code>')
    middle = (html.escape(report["generated_utc"]) + '</code></p><p>Overall status: <strong>' +
              html.escape(report["overall_status"]) + '</strong></p><p>Reports: ' +
              str(report["reports_total"]) + '; warning statuses: ' +
              str(report["reports_with_warning_status"]) +
              '</p><table><thead><tr><th>File</th><th>Schema</th><th>Status</th></tr></thead><tbody>')
    return head + middle + "".join(rows) + "</tbody></table><h2>Caveats</h2><ul>" + caveats + "</ul></body></html>\n"

def main(argv=None):
    ap = argparse.ArgumentParser(description="Aggregate QWP-777 JSON diagnostics into JSON and HTML health reports.")
    ap.add_argument("reports", nargs="+", help="input JSON diagnostic reports")
    ap.add_argument("--json", default="health-report.json", help="JSON output path")
    ap.add_argument("--html", default="health-report.html", help="HTML output path")
    args = ap.parse_args(argv)
    try:
        report = build_health_report(args.reports)
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        Path(args.html).write_text(render_html(report), encoding="utf-8")
        print(json.dumps({"overall_status": report["overall_status"], "reports_total": report["reports_total"], "json": args.json, "html": args.html}))
        return 0
    except (HealthReportError, OSError) as exc:
        print(f"qwp777-health-report: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
