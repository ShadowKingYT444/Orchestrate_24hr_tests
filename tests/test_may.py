import csv
from pathlib import Path
import tempfile
import unittest

from orchestrate_eval.historical import evaluate_historical
from orchestrate_eval.public_validation import run_controls


class MayTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.inputs = [['Issue', 'Subject', 'Company'], ['First\n ticket', 'One', 'Claude'], ['Second ticket', 'Two', 'Visa']]
        self.headers = ['issue', 'subject', 'company', 'response', 'product_area', 'status', 'request_type', 'justification']
        self.rows = [dict(zip(self.headers, ['First ticket', 'One', 'Claude', 'Synthetic reply', 'arbitrary category', 'replied', 'product_issue', 'Synthetic reason'])),
                     dict(zip(self.headers, ['Second ticket', 'Two', 'Visa', 'Synthetic escalation', '', 'escalated', 'bug', 'Synthetic reason']))]
        self.input_path = self.root / 'inputs.csv'
        with self.input_path.open('w', newline='') as stream:
            csv.writer(stream).writerows(self.inputs)

    def evaluate(self, rows=None, headers=None):
        path = self.root / 'output.csv'
        with path.open('w', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=headers or self.headers, extrasaction='ignore')
            writer.writeheader(); writer.writerows(self.rows if rows is None else rows)
        return evaluate_historical(path, {'plugin': 'may26_schema', 'input_csv': str(self.input_path)})

    def assertValid(self, checks):
        self.assertFalse(any(check['status'] == 'fail' for check in checks), checks)
        self.assertTrue(any(check['status'] == 'unknown' for check in checks), checks)

    def test_actual_style_whitespace_extra_columns_and_blank_area(self):
        self.assertValid(self.evaluate())

    def test_reordered_headers_are_allowed(self):
        self.assertValid(self.evaluate(headers=self.headers[::-1]))

    def test_missing_extra_or_reordered_rows(self):
        for rows in (self.rows[:-1], self.rows + [self.rows[0]], self.rows[::-1]):
            self.assertTrue(any(check['status'] == 'fail' for check in self.evaluate(rows)))

    def test_no_echo_identity_remains_unknown(self):
        headers = [field for field in self.headers if field not in {'issue', 'subject', 'company'}]
        checks = self.evaluate(headers=headers)
        self.assertValid(checks)
        self.assertEqual(next(check['status'] for check in checks if check['name'] == 'May echoed input identity'), 'unknown')

    def test_invalid_enums_blank_text_and_altered_input(self):
        for field, value in (('status', 'approved'), ('request_type', 'feature'), ('response', ''), ('justification', '\t '), ('issue', 'changed')):
            rows = [dict(row) for row in self.rows]; rows[0][field] = value
            self.assertTrue(any(check['status'] == 'fail' for check in self.evaluate(rows)), (field, value))

    def test_required_field_missing(self):
        self.assertEqual(self.evaluate(headers=[field for field in self.headers if field != 'request_type'])[0]['status'], 'fail')

    def test_ambiguous_header_aliases_refused(self):
        self.assertEqual(self.evaluate(headers=self.headers + ['Status'])[0]['status'], 'fail')

    def test_semantically_wrong_but_valid_output_stays_unknown(self):
        rows = [dict(row, status='escalated' if row['status'] == 'replied' else 'replied') for row in self.rows]
        rows[0]['response'] = 'Synthetic invented policy'
        self.assertValid(self.evaluate(rows))

    def test_controls_detect_structure_and_disclose_semantic_blind_spots(self):
        results = run_controls(self.input_path, self.headers, self.rows, self.root)
        self.assertEqual(len(results), 12)
        self.assertTrue(all(result['calibration_pass'] for result in results), results)
        self.assertEqual(sum(result['observed'] == 'fail' for result in results), 9)
        self.assertEqual(sum(result['observed'] == 'unknown' for result in results), 3)
