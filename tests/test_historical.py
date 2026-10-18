import csv
import os
from pathlib import Path
import tempfile
import unittest

from orchestrate_eval.historical import evaluate_historical, JUNE_HEADERS, SEPTEMBER_HEADERS


class HistoricalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, name, headers, rows):
        path = self.root / name
        with path.open('w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(rows)
        return path

    def evaluate(self, plugin, input_headers, input_rows, headers, rows):
        inp = self.write('input.csv', input_headers, input_rows)
        out = self.write('output.csv', headers, rows)
        return evaluate_historical(out, {'plugin': plugin, 'input_csv': str(inp)})

    def june(self, edits=None, input_count=1, output_count=1, headers=None):
        row = ['u1', 'images/one.jpg;images/two.jpg', 'Synthetic dent claim', 'car', 'true', 'Synthetic reason', 'none', 'dent', 'door', 'supported', 'Synthetic explanation', 'one;two', 'true', 'low']
        for key, value in (edits or {}).items():
            row[JUNE_HEADERS.index(key)] = value
        original = ['u1', 'images/one.jpg;images/two.jpg', 'Synthetic dent claim', 'car']
        return self.evaluate('june26_schema', JUNE_HEADERS[:4], [original] * input_count, headers or JUNE_HEADERS, [row] * output_count)

    def september(self, edits=None, duplicate=False, input_duplicate=False):
        row = ['r1', '30', 'affordable_with_plan', 'partial_payment', '2026-09-01:30|2026-09-10:70', '2026-09-10', 'none', 'Synthetic example only']
        for key, value in (edits or {}).items():
            row[SEPTEMBER_HEADERS.index(key)] = value
        return self.evaluate('september26_schema', ['request_id', 'requested_amount', 'request_date', 'desired_completion_date'], [['r1', '100', '2026-09-01', '2026-09-30']] * (2 if input_duplicate else 1), SEPTEMBER_HEADERS, [row] * (2 if duplicate else 1))

    def assertValid(self, checks):
        self.assertFalse(any(c['status'] == 'fail' for c in checks), checks)
        self.assertTrue(any(c['status'] == 'unknown' for c in checks), checks)
        self.assertTrue(all(set(c) == {'name', 'status', 'kind', 'evidence'} for c in checks))

    def assertInvalid(self, checks):
        self.assertTrue(any(c['status'] == 'fail' for c in checks), checks)

    def test_june_valid(self):
        self.assertValid(self.june())

    def test_june_preserves_duplicate_rows(self):
        self.assertValid(self.june(input_count=2, output_count=2))
        self.assertInvalid(self.june(input_count=2))

    def test_corrupt_and_reordered_headers(self):
        headers = JUNE_HEADERS.copy()
        headers[0], headers[1] = headers[1], headers[0]
        self.assertInvalid(self.june(headers=headers))
        headers[0] = 'invalid'
        self.assertInvalid(self.june(headers=headers))

    def test_june_bad_values(self):
        for key, value in [('claim_object', 'bike'), ('valid_image', 'True'), ('object_part', 'hinge'), ('risk_flags', 'none;blurry_image'), ('supporting_image_ids', 'other'), ('severity', 'severe'), ('user_id', 'changed')]:
            with self.subTest(key=key):
                self.assertInvalid(self.june({key: value}))

    def test_september_valid(self):
        self.assertValid(self.september())

    def test_duplicate_ids(self):
        self.assertInvalid(self.september(duplicate=True))
        self.assertInvalid(self.september(input_duplicate=True))

    def test_coverage(self):
        self.assertInvalid(self.september({'request_id': 'other'}))

    def test_nonfinite_and_bounds(self):
        for value in ['NaN', 'sNaN', 'Infinity', '-Infinity', '-1', '101', 'junk']:
            with self.subTest(value=value):
                self.assertInvalid(self.september({'amount_safe_to_pay': value}))

    def test_plan_issues(self):
        for value in ['none', '', '2026-09-10:70|2026-09-01:30', '2026-09-01:30|2026-09-10:69', '2026-09-01:NaN|2026-09-10:70', '2026-9-01:30|2026-09-10:70', '2026-09-01:-30|2026-09-10:130', 'garbage']:
            with self.subTest(value=value):
                self.assertInvalid(self.september({'payment_plan': value}))

    def test_partial_constraints(self):
        for key, value in [('affordability_status', 'affordable_now'), ('amount_safe_to_pay', '0'), ('earliest_date_for_full_payment', '2026-10-01'), ('earliest_date_for_full_payment', '')]:
            self.assertInvalid(self.september({key: value}))

    def test_now_date(self):
        self.assertInvalid(self.september({'affordability_status': 'affordable_now', 'recommended_payment_method': 'full_payment', 'payment_plan': '2026-09-01:100'}))
        self.assertValid(self.september({'amount_safe_to_pay': '100', 'affordability_status': 'affordable_now', 'recommended_payment_method': 'full_payment', 'payment_plan': '2026-09-01:100', 'earliest_date_for_full_payment': '2026-09-01'}))

    def test_relative_input_path(self):
        self.june()
        old = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertValid(evaluate_historical('output.csv', {'plugin': 'june26_schema', 'input_csv': 'input.csv'}))
        finally:
            os.chdir(old)

    def test_bad_csv_and_size(self):
        inp = self.write('input.csv', JUNE_HEADERS[:4], [])
        out = self.root / 'output.csv'
        out.write_text('x,x\na,b\n')
        task = {'plugin': 'june26_schema', 'input_csv': str(inp)}
        self.assertInvalid(evaluate_historical(out, task))
        out.write_bytes(b'a' * 5_000_001)
        self.assertInvalid(evaluate_historical(out, task))

    def test_symlink(self):
        inp = self.write('input.csv', JUNE_HEADERS[:4], [])
        link = self.root / 'link.csv'
        link.symlink_to(inp)
        self.assertInvalid(evaluate_historical(link, {'plugin': 'june26_schema', 'input_csv': str(inp)}))

    def test_requires_input(self):
        with self.assertRaises(ValueError):
            evaluate_historical('missing', {'plugin': 'june26_schema'})

    def test_june_blank_reasons(self):
        for field in ('evidence_standard_met_reason', 'claim_status_justification'):
            self.assertInvalid(self.june({field: '  '}))

    def test_september_spending_change_syntax(self):
        for value in ('', 'stop:', 'stop:e|reduce_to:e:10', 'stop:a|stop:b|stop:c|stop:d',
                      'reduce_to:e:NaN', 'reduce_to:e:-1', 'reduce_to:e', 'stop:e:10', 'junk', 'none|stop:e'):
            with self.subTest(value=value):
                self.assertInvalid(self.september({'spending_changes_needed': value}))
        for value in ('stop:e', 'reduce_to:e:0', 'stop:e1|reduce_to:e2:10.50'):
            with self.subTest(value=value):
                self.assertValid(self.september({'spending_changes_needed': value}))

    def test_september_blank_explanation(self):
        self.assertInvalid(self.september({'decision_explanation': '\t '}))

    def test_partial_remainder_uses_exact_decimal_arithmetic(self):
        tiny = '0.00000000000000000000000000001'
        self.assertInvalid(self.september({'amount_safe_to_pay': tiny, 'payment_plan': f'2026-09-01:{tiny}|2026-09-10:100'}))
        exact = '99.99999999999999999999999999999'
        self.assertValid(self.september({'amount_safe_to_pay': tiny, 'payment_plan': f'2026-09-01:{tiny}|2026-09-10:{exact}'}))


if __name__ == '__main__':
    unittest.main()
