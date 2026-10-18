import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from orchestrate_eval import public_validation as public


@unittest.skipUnless(shutil.which('git'), 'Git is needed only for public-provenance integration tests')
class PublicCalibrationTests(unittest.TestCase):
    """Entirely authored synthetic repositories; never download or run an agent."""
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.candidate = self.root / 'candidate'; self.candidate.mkdir()
        self.official = self.root / 'official'; self.official.mkdir()
        self.files = {
            'problem_statement.md': 'Synthetic specification, not third-party content.\n',
            'support_tickets/support_tickets.csv': 'Issue,Subject,Company\nFirst ticket,One,Claude\nSecond ticket,Two,Visa\n',
            'support_tickets/sample_support_tickets.csv': 'Issue,Subject,Company,Status\nUnrelated sample,Other,None,Replied\n',
            'support_tickets/output.csv': 'issue,subject,company,response,product_area,status,request_type,justification\nFirst ticket,One,Claude,Example reply,general,replied,product_issue,Example reason\nSecond ticket,Two,Visa,Example reply,general,escalated,bug,Example reason\n',
            'code/main.py': 'raise RuntimeError("Candidate must never execute")\n',
            'code/README.md': 'Synthetic setup\n',
            'code/requirements.txt': '',
        }
        for path, content in self.files.items():
            for root in (self.candidate, self.official):
                if root == self.official and (path == 'support_tickets/output.csv' or path.startswith('code/')):
                    continue
                target = root / path; target.parent.mkdir(parents=True, exist_ok=True); target.write_text(content)
        self.commits = []
        for root in (self.candidate, self.official):
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', '-C', str(root), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(root), '-c', 'user.name=Synthetic Test', '-c', 'user.email=test@example.invalid',
                            '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic test fixtures'], check=True)
            self.commits.append(subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip())
        self.hashes = {path: hashlib.sha256(content.encode()).hexdigest() for path, content in self.files.items() if not path.startswith('code/')}

    def calibration(self):
        with patch.object(public, 'CANDIDATE_COMMIT', self.commits[0]), patch.object(public, 'OFFICIAL_COMMIT', self.commits[1]), patch.object(public, 'ARTIFACTS', self.hashes):
            return public.validate_public(self.candidate, self.official, self.root / 'reports')

    def test_end_to_end_only_parses_candidate(self):
        result = self.calibration()
        self.assertEqual(result['calibration_status'], 'pass')
        self.assertEqual(result['source']['python_files_parsed'], 1)
        self.assertFalse(result['source']['executed_or_imported'])
        self.assertIsNone(result['output']['accuracy'])
        self.assertIsNone(result['output']['official_score'])
        self.assertEqual(result['label_audit']['sample_input_overlap'], 0)
        self.assertFalse(result['coding_transcript']['available'])
        self.assertEqual(result['runtime']['model_calls_made_by_this_validation'], 0)
        self.assertEqual(json.loads((self.root/'reports/validation.json').read_text())['calibration_status'], 'pass')

    def test_modified_saved_output_refused(self):
        with (self.candidate/'support_tickets/output.csv').open('a') as stream:
            stream.write('\n')
        with self.assertRaisesRegex(ValueError, 'artifact differs'):
            self.calibration()

    def test_modified_source_refused(self):
        (self.candidate/'code/main.py').write_text('print("changed")\n')
        with self.assertRaisesRegex(ValueError, 'Source working copy differs'):
            self.calibration()

    def test_extra_python_source_refused(self):
        (self.candidate/'code/extra.py').write_text('pass\n')
        with self.assertRaisesRegex(ValueError, 'Unexpected/missing source'):
            self.calibration()

    def test_untracked_proxy_paths_refused(self):
        (self.candidate/'code/tests').mkdir()
        with self.assertRaisesRegex(ValueError, 'Unexpected/missing source'):
            self.calibration()

    def test_wrong_pin_refused(self):
        with self.assertRaisesRegex(ValueError, 'exact pinned checkout'):
            public.validate_public(self.candidate, self.official, self.root/'reports')
