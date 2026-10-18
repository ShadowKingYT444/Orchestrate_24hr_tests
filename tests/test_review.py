import unittest
from orchestrate_eval.review import validate_review

class ReviewTests(unittest.TestCase):
    def test_empty_is_unknown(self):
        checks = validate_review({"origin":"human","reviewer":"test","criteria":{}})
        self.assertTrue(all(c["status"] == "unknown" for c in checks))
    def test_claim_without_evidence_rejected(self):
        with self.assertRaises(ValueError):
            validate_review({"origin":"human","reviewer":"test","criteria":{"robustness":{"rating":"strong","evidence":[]}}})
    def test_advisory_never_objective_pass(self):
        checks = validate_review({"origin":"configured_judge","reviewer":"test","criteria":{"robustness":{"rating":"strong","evidence":["tests/test_core.py timeout test"]}}})
        self.assertEqual(checks[2]["kind"], "subjective")
        self.assertEqual(checks[2]["status"], "unknown")

class CorruptionTests(unittest.TestCase):
    def test_duplicate_json_keys_and_nonfinite(self):
        from orchestrate_eval.checks import strict_json
        for raw in ['{"answers":{"x":0,"x":1}}', '{"x":NaN}', '{"x":Infinity}']:
            with self.assertRaises(ValueError):
                strict_json(raw)
    def test_fast_log_overflow(self):
        import sys
        from orchestrate_eval.runner import run_command
        report = run_command([sys.executable, '-c', 'import os; os.write(1,b"x"*1100000)'], '.', trusted=True)
        self.assertTrue(report['log_limit_exceeded'])
        self.assertEqual(report['status'], 'fail')
