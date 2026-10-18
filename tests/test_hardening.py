import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from orchestrate_eval.checks import strict_json
from orchestrate_eval.cli import main
from orchestrate_eval.fileio import read_bounded
from orchestrate_eval.runner import run_command


class HardeningTests(unittest.TestCase):
    def test_json_exponent_overflow(self):
        for value in ('1e999', '-1e999', 'NaN', 'Infinity'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                strict_json('{"x":' + value + '}')

    def test_json_nesting(self):
        with self.assertRaises(ValueError):
            strict_json('[' * 2000 + '0' + ']' * 2000)

    def test_command_must_be_a_list(self):
        for command in ('echo', {'echo': 'argument'}, ('echo',), [], [''], [12]):
            with self.subTest(command=command), self.assertRaises(ValueError):
                run_command(command, '.', trusted=True)

    def test_input_types_and_bounds(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / 'input'
            path.write_bytes(b'123456')
            self.assertEqual(read_bounded(path, 6), b'123456')
            with self.assertRaises(ValueError):
                read_bounded(path, 5)
            link = root / 'link'; link.symlink_to(path)
            with self.assertRaises(ValueError):
                read_bounded(link)
            with self.assertRaises((ValueError, OSError)):
                read_bounded(root)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'POSIX FIFO test')
    def test_fifo_rejected_without_blocking(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fifo'
            os.mkfifo(path)
            with self.assertRaises(ValueError):
                read_bounded(path)

    def test_unknown_plugin_oversize_output_report(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            task = root / 'task.json'; task.write_text('{"plugin":"unknown"}')
            output = root / 'large'
            with output.open('wb') as stream:
                stream.truncate(5_000_001)
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded read')):
                code = main(['evaluate', '--task', str(task), '--output', str(output), '--report-dir', str(root/'report')])
            self.assertEqual(code, 1)
            report = json.loads((root/'report/report.json').read_text())
            self.assertIsNone(report['output_sha256'])
            self.assertEqual(report['status'], 'fail')

    def test_nonstring_profile_clean_error(self):
        with tempfile.TemporaryDirectory() as folder:
            task = Path(folder) / 'task.json'
            task.write_text('{"profile":{},"plugin":"synthetic_exact","expected":{"x":1}}')
            self.assertEqual(main(['evaluate', '--task', str(task), '--output', str(task)]), 2)

    def test_runner_does_not_inherit_credentials(self):
        with patch.dict(os.environ, {'ORCHESTRATE_TEST_SECRET': 'not-inherited'}):
            report = run_command([sys.executable, '-c', 'import os; print(os.environ.get("ORCHESTRATE_TEST_SECRET"))'], '.', trusted=True)
        self.assertEqual(report['stdout'].strip(), 'None')
