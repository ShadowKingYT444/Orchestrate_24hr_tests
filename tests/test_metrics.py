import copy
import csv
import json
from pathlib import Path
import tempfile
import unittest

from orchestrate_eval.cli import main
from orchestrate_eval.metrics import evaluate_labelled, compare_reports


ROOT = Path(__file__).resolve().parents[1]


class LabelledMetricsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.reference = self.write('reference.csv', [['id', 'label', 'safety'], ['1', 'a', 'safe'], ['2', 'b', 'review']])
        self.task = {'plugin': 'labelled_csv', 'profile': 'local-v1', 'reference_csv': str(self.reference),
                     'id_column': 'id', 'fields': ['label', 'safety']}

    def write(self, name, rows):
        path = self.root / name
        with path.open('w', newline='', encoding='utf-8') as stream:
            csv.writer(stream).writerows(rows)
        return path

    def evaluate(self, rows):
        return evaluate_labelled(self.write('candidate.csv', rows), self.task)

    def test_reordered_exact_match(self):
        checks, metrics = self.evaluate([['safety', 'id', 'label'], ['review', '2', 'b'], ['safe', '1', 'a']])
        self.assertTrue(all(check['status'] == 'pass' for check in checks))
        self.assertEqual(metrics['micro_accuracy'], 1)
        self.assertEqual(metrics['exact_row_accuracy'], 1)
        self.assertEqual(len(metrics['per_case']), 2)

    def test_mismatch_confusion(self):
        checks, metrics = self.evaluate([['id', 'label', 'safety'], ['1', 'b', 'safe'], ['2', 'b', 'review']])
        self.assertEqual(metrics['micro_accuracy'], .75)
        self.assertEqual(metrics['exact_row_accuracy'], .5)
        self.assertEqual(metrics['fields']['label']['accuracy'], .5)
        self.assertIn({'expected': 'a', 'predicted': 'b', 'count': 1}, metrics['fields']['label']['confusion'])
        self.assertEqual(metrics['per_case'][0]['mismatched_fields'], ['label'])
        self.assertTrue(any(check['status'] == 'fail' for check in checks))

    def test_missing_and_extra_ids(self):
        checks, metrics = self.evaluate([['id', 'label', 'safety'], ['1', 'a', 'safe'], ['other', 'b', 'review']])
        self.assertEqual(metrics['micro_accuracy'], .5)
        self.assertEqual(metrics['missing_ids'], ['2'])
        self.assertEqual(metrics['unexpected_ids'], ['other'])
        self.assertFalse(next(case for case in metrics['per_case'] if case['id'] == '2')['present'])
        self.assertEqual(checks[0]['status'], 'fail')

    def test_empty_candidate_counts_missing(self):
        checks, metrics = self.evaluate([['id', 'label', 'safety']])
        self.assertEqual(metrics['micro_accuracy'], 0)
        self.assertEqual(len(metrics['missing_ids']), 2)

    def test_duplicate_ids_no_metrics(self):
        checks, metrics = self.evaluate([['id', 'label', 'safety'], ['1', 'a', 'safe'], ['1', 'b', 'review']])
        self.assertIsNone(metrics)
        self.assertEqual(checks[0]['status'], 'fail')

    def test_missing_columns(self):
        checks, metrics = self.evaluate([['id', 'label'], ['1', 'a']])
        self.assertIsNone(metrics)
        self.assertEqual(checks[0]['status'], 'fail')

    def test_reference_duplicates_rejected(self):
        self.write('reference.csv', [['id', 'label', 'safety'], ['1', 'a', 'safe'], ['1', 'b', 'review']])
        with self.assertRaises(ValueError):
            self.evaluate([['id', 'label', 'safety']])

    def test_bad_config(self):
        for update in ({'fields': []}, {'fields': ['id']}, {'fields': ['label', 'label']}, {'fields': 'label'}, {'id_column': None}):
            task = dict(self.task, **update)
            with self.subTest(update=update), self.assertRaises(ValueError):
                evaluate_labelled(self.reference, task)

    def test_no_semantic_or_numeric_normalization(self):
        self.write('reference.csv', [['id', 'label', 'safety'], ['1', '1.0', 'safe']])
        _, metrics = self.evaluate([['id', 'label', 'safety'], ['1', '1', 'SAFE']])
        self.assertEqual(metrics['micro_accuracy'], 0)

    def test_cli_compare_and_binding(self):
        task_path = self.root / 'task.json'; task_path.write_text(json.dumps(self.task))
        reports = []
        for label in ('a', 'b'):
            folder = self.root / label
            code = main(['evaluate', '--task', str(task_path), '--output', str(self.reference), '--label', label, '--report-dir', str(folder)])
            self.assertEqual(code, 2)  # Source/transcript remain unknown.
            report = json.loads((folder/'report.json').read_text())
            self.assertEqual(report['metrics']['micro_accuracy'], 1)
            self.assertEqual(report['scorecards']['output']['objective']['fail'], 0)
            reports.append(report)
        result = compare_reports(reports)
        self.assertIsNone(result['official_score'])
        self.assertEqual([row['label'] for row in result['configurations']], ['a', 'b'])
        self.assertEqual(main(['compare', str(self.root/'a/report.json'), str(self.root/'b/report.json'), '--report-dir', str(self.root/'comparison')]), 0)
        self.assertTrue((self.root/'comparison/comparison.html').exists())
        changed = copy.deepcopy(reports)
        changed[1]['metrics']['reference_sha256'] = 'different'
        with self.assertRaises(ValueError):
            compare_reports(changed)
        changed = copy.deepcopy(reports)
        changed[1]['task_sha256'] = 'different'
        with self.assertRaises(ValueError):
            compare_reports(changed)
        with self.assertRaises(ValueError):
            compare_reports(reports[:1])

    def test_reference_hash_changes(self):
        _, before = evaluate_labelled(self.reference, self.task)
        with self.reference.open('a') as stream:
            stream.write('3,c,safe\n')
        _, after = evaluate_labelled(self.reference, self.task)
        self.assertNotEqual(before['reference_sha256'], after['reference_sha256'])

    def test_large_details_are_bounded_and_aggregates_complete(self):
        rows = [['id', 'label', 'safety']] + [[str(index), 'category-' + str(index), 'safe'] for index in range(2000)]
        self.write('reference.csv', rows)
        _, metrics = self.evaluate(rows)
        self.assertEqual(metrics['rows'], 2000)
        self.assertEqual(metrics['micro_accuracy'], 1)
        self.assertEqual(len(metrics['per_case']), 1000)
        self.assertTrue(metrics['case_details_truncated'])
        self.assertEqual(metrics['fields']['label']['confusion_entry_count'], 2000)
        self.assertTrue(metrics['fields']['label']['confusion_truncated'])
        self.assertEqual(len(metrics['fields']['label']['confusion']), 200)

    def test_malformed_compare_clean_error(self):
        for reports in ([None, None], [[], []], [{'metrics': ['bad']}, {}]):
            with self.subTest(reports=reports), self.assertRaises(ValueError):
                compare_reports(reports)
