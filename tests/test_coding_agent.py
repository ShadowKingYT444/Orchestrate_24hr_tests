"""Adapter regressions. Mocked Codex completions are not live model validation."""
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from orchestrate_eval.coding_agent import inspect_codex, run_coding_agent, codex_environment
from orchestrate_eval.cli import main


class CodingAgentTests(unittest.TestCase):
    def preflight(self):
        return {'executable': '/mock/codex', 'auth_type': 'chatgpt', 'version': 'codex-cli mock'}

    def result(self, success=False):
        return {'status': 'pass' if success else 'fail', 'stdout': '{"type":"turn.completed"}\n' if success else '',
                'stderr': '' if success else 'Error: Read-only file system (os error 30)',
                'exit_code': 0 if success else 1, 'wall_seconds': .01, 'timed_out': False,
                'log_limit_exceeded': False, 'command': ['mock']}

    def test_optins_and_budget_checked_before_preflight(self):
        with patch('orchestrate_eval.coding_agent.inspect_codex') as inspect:
            for kwargs in ({}, {'trusted': True}, {'allow_model_turn': True},
                           {'trusted': True, 'allow_model_turn': True, 'remaining_usage_percent': 10},
                           {'trusted': True, 'allow_model_turn': True, 'remaining_usage_percent': math.nan},
                           {'trusted': True, 'allow_model_turn': True, 'timeout': math.inf}):
                with self.assertRaises(ValueError):
                    run_coding_agent('/tmp/unused-coding-agent-test', 'model', **kwargs)
            inspect.assert_not_called()

    def test_missing_executable(self):
        with patch('orchestrate_eval.coding_agent.shutil.which', return_value=None):
            self.assertIn('not found', inspect_codex()['blocker'])

    def test_custom_executable_requires_explicit_trust(self):
        with patch('orchestrate_eval.coding_agent.shutil.which') as which:
            with self.assertRaises(ValueError):
                inspect_codex('/untrusted/program')
            which.assert_not_called()

    def test_any_existing_evidence_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp, patch('orchestrate_eval.coding_agent.inspect_codex') as inspect:
            path = Path(tmp) / 'coding-stderr.txt'
            path.write_text('original')
            with self.assertRaises(ValueError):
                run_coding_agent(tmp, 'model', trusted=True, allow_model_turn=True)
            inspect.assert_not_called()
            self.assertEqual(path.read_text(), 'original')

    def test_auth_inspection_redacts_api_preview(self):
        def reply(command, **kwargs):
            return subprocess.CompletedProcess(command, 0, 'codex-cli test\n' if '--version' in command else 'Logged in using an API key: sk-private-preview\n', '')
        with patch('orchestrate_eval.coding_agent.shutil.which', return_value='/mock/codex'), patch('orchestrate_eval.coding_agent.subprocess.run', side_effect=reply):
            report = inspect_codex()
        self.assertEqual(report['auth_type'], 'api_key_refused')
        self.assertNotIn('sk-private', json.dumps(report))

    def test_no_api_secret_in_native_environment(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'secret', 'OTHER_SECRET': 'secret', 'HOME': '/native-home'}):
            env = codex_environment()
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('OTHER_SECRET', env)
        self.assertEqual(env['HOME'], '/native-home')

    def test_no_login_or_paid_fallback(self):
        with tempfile.TemporaryDirectory() as tmp, patch('orchestrate_eval.coding_agent.inspect_codex', return_value={'blocker': 'Login not confirmed'}), patch('orchestrate_eval.coding_agent.run_command') as execute:
            report = run_coding_agent(tmp, 'model', trusted=True, allow_model_turn=True)
            execute.assert_not_called()
            self.assertEqual(report['status'], 'blocked')
            self.assertIsNone(report['benchmark_report'])

    def test_startup_failure_preserves_exact_evidence_no_score(self):
        with tempfile.TemporaryDirectory() as tmp, patch('orchestrate_eval.coding_agent.inspect_codex', return_value=self.preflight()), patch('orchestrate_eval.coding_agent.run_command', return_value=self.result()) as execute, patch('orchestrate_eval.coding_agent.run_benchmark') as benchmark:
            report = run_coding_agent(tmp, 'model', trusted=True, allow_model_turn=True)
            benchmark.assert_not_called()
            self.assertFalse(report['model_turn_completed'])
            self.assertFalse(report['source_changed'])
            self.assertIn('Read-only file system', (Path(tmp) / 'coding-stderr.txt').read_text())
            self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', execute.call_args.args[0])
            self.assertIn('--ephemeral', execute.call_args.args[0])
            with self.assertRaises(ValueError):
                run_coding_agent(tmp, 'model', trusted=True, allow_model_turn=True)

    def test_mocked_completion_connects_produced_agent_benchmark_and_genuine_export(self):
        # Only integration wiring is mocked here. This is never a real Codex score.
        benchmark_report = {'machine_component_mean_85': 40, 'output_score_100': None}
        with tempfile.TemporaryDirectory() as tmp, patch('orchestrate_eval.coding_agent.inspect_codex', return_value=self.preflight()), patch('orchestrate_eval.coding_agent.run_command', return_value=self.result(True)), patch('orchestrate_eval.coding_agent.run_benchmark', return_value=benchmark_report) as benchmark, patch('orchestrate_eval.judging.export_bundle', return_value={'bundle_id': 'mock'}) as export:
            report = run_coding_agent(tmp, 'model', trusted=True, allow_model_turn=True, remaining_usage_percent=80)
            self.assertEqual(report['status'], 'executed')
            self.assertTrue(report['model_turn_completed'])
            self.assertIsNone(report['output_score_100'])
            self.assertEqual(benchmark.call_args.args[4:7], ('holdout', 1, 5))
            self.assertEqual(export.call_args.args[2], Path(tmp) / 'coding-transcript.json')
            transcript = json.loads((Path(tmp) / 'coding-transcript.json').read_text())
            self.assertEqual(transcript['events'][0]['role'], 'user')
            self.assertIn('turn.completed', transcript['events'][1]['content'])

    def test_explicit_mock_cli_process_then_real_produced_adapter_execution(self):
        # This authored emulator verifies process/artifact/runtime wiring only.
        # It is not Codex, a model call, or an authentic model coding transcript.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / 'synthetic_cli.py'
            fake.write_text('#!' + sys.executable + '\n' +
                'import json\nfrom pathlib import Path\n' +
                'p=Path("agent.py");s=p.read_text()\n' +
                's=s.replace("facts[\'invoice_currency\'] = \'USD\'\\n            response = \'The invoice currency is USD.\'", "response = f\\\"The invoice currency is {facts[\'invoice_currency\']}.\\\"")\n' +
                's=s.replace("status, action = \'replied\', \'answer\'\\n            response = \'An admin", "status, action = \'escalated\', \'handoff\'\\n            response = \'An admin")\n' +
                'p.write_text(s)\n' +
                'print(json.dumps({"type":"turn.started"}))\n' +
                'print(json.dumps({"type":"turn.completed"}))\n')
            fake.chmod(0o700)
            with patch('orchestrate_eval.coding_agent.inspect_codex', return_value={'executable': str(fake), 'auth_type': 'chatgpt', 'version': 'SYNTHETIC UNIT EMULATOR'}):
                report = run_coding_agent(root / 'reports', 'mock-model', trusted=True, allow_model_turn=True)
            self.assertEqual(report['status'], 'executed')
            self.assertTrue(report['source_changed'])
            self.assertEqual(report['machine_component_mean_85'], 85)
            self.assertIsNone(report['output_score_100'])
            runtime = json.loads((root / 'reports/benchmark/benchmark.json').read_text())
            self.assertEqual(len(runtime['runs']), 12)
            self.assertTrue(any(item['read_document_ids'] for item in runtime['runs']))
            bundle = json.loads((root / 'reports/judge-bundle.json').read_text())
            self.assertIn('engineering_rigor', bundle['rubrics']['code'])
            self.assertTrue(any(item['source'].startswith('transcript/') for item in bundle['untrusted_evidence_files']))

    def test_cli_fails_closed_without_optin(self):
        self.assertEqual(main(['coding-agent', 'run', '--model', 'model']), 2)


if __name__ == '__main__':
    unittest.main()
