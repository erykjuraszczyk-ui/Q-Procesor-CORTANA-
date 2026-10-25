import json, tempfile, unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/"src"))
from qwp777_health_report import build_health_report, render_html, HealthReportError
class HealthReportTests(unittest.TestCase):
 def test_aggregates_reports(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"soak.json"; p.write_text(json.dumps({"report_schema":"qwp777-soak-report-1","summary":{"status":"no_suspicious_growth"}}))
   r=build_health_report([p]); self.assertEqual(r["reports_total"],1); self.assertEqual(r["overall_status"],"informational_or_ok")
 def test_flags_anomaly_candidate(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"analysis.json"; p.write_text(json.dumps({"report_schema":"qwp777-stability-analysis-1","summary":{"status":"anomaly_candidate"}}))
   self.assertEqual(build_health_report([p])["overall_status"],"review_required")
 def test_html_escapes_filename(self):
  r={"generated_utc":"now","overall_status":"ok","reports_total":1,"reports_with_warning_status":0,"reports":[{"file":"<script>","report_schema":"x","status":"ok"}],"caveats":[]}
  self.assertNotIn("<script>",render_html(r)); self.assertIn("&lt;script&gt;",render_html(r))
 def test_rejects_non_object(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"bad.json"; p.write_text("[]")
   with self.assertRaises(HealthReportError): build_health_report([p])
if __name__=="__main__": unittest.main()
