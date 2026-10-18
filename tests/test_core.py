import json
import sys
import tempfile
import unittest
from pathlib import Path
from orchestrate_eval.checks import synthetic_exact, transcript_checks
from orchestrate_eval.cli import main
from orchestrate_eval.runner import run_command

ROOT = Path(__file__).resolve().parents[1]

class CoreTests(unittest.TestCase):
    def test_good_bad(self):
        task = json.loads((ROOT / "examples/task.json").read_text())
        for name, expected in [("good", True), ("bad", False)]:
            checks = synthetic_exact(json.loads((ROOT / f"examples/{name}/output.json").read_text()), task)
            self.assertEqual(all(c["status"] == "pass" for c in checks), expected)

    def test_bool_is_not_int(self):
        self.assertEqual(synthetic_exact({"answers":{"x":True}}, {"expected":{"x":1}})[0]["status"], "fail")

    def test_missing_answers(self):
        self.assertEqual(synthetic_exact({}, {"expected":{"x":1}})[0]["status"], "fail")

    def test_transcript_unknown_authenticity(self):
        checks = transcript_checks(ROOT / "examples/good/transcript.json")
        self.assertEqual(next(c for c in checks if c["name"] == "transcript authenticity")["status"], "unknown")

    def test_opt_in(self):
        with self.assertRaises(ValueError):
            run_command([sys.executable, "-c", "print('x')"], ROOT)

    def test_runner_success(self):
        report = run_command([sys.executable, "-c", "print('ok')"], ROOT, trusted=True)
        self.assertEqual(report["status"], "pass")
        self.assertIn("ok", report["stdout"])
        self.assertIsNone(report["tokens"])

    def test_timeout(self):
        report = run_command([sys.executable, "-c", "import time; time.sleep(5)"], ROOT, timeout=.05, trusted=True)
        self.assertTrue(report["timed_out"])

    def test_failure(self):
        report = run_command([sys.executable, "-c", "raise SystemExit(9)"], ROOT, trusted=True)
        self.assertEqual(report["exit_code"], 9)

    def test_cli_report_and_no_fake_score(self):
        with tempfile.TemporaryDirectory() as temp:
            code = main(["evaluate", "--task", str(ROOT/"examples/task.json"), "--output", str(ROOT/"examples/good/output.json"), "--report-dir", temp])
            self.assertEqual(code, 2)  # missing source/transcript = incomplete
            report = json.loads((Path(temp)/"report.json").read_text())
            self.assertIsNone(report["official_score"])
            self.assertFalse(report["coverage"]["renormalized"])
            self.assertEqual(report["coverage"]["maximum_in_scope_weight"], 70)
            self.assertTrue((Path(temp)/"report.html").exists())

    def test_unknown_plugin_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"task.json"; path.write_text('{"plugin":"missing"}')
            code = main(["evaluate", "--task", str(path), "--output", str(ROOT/"examples/good/output.json"), "--report-dir", temp])
            self.assertEqual(code, 2)
            report = json.loads((Path(temp)/"report.json").read_text())
            self.assertEqual(report["checks"]["output"][0]["status"], "unknown")

    def test_malformed_json(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"task.json"; path.write_text('{broken')
            self.assertEqual(main(["evaluate", "--task", str(path), "--output", str(path)]), 2)

if __name__ == "__main__":
    unittest.main()
