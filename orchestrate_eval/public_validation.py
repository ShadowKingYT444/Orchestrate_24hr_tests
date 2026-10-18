"""Reproducible, non-executing calibration on pinned public winner artifacts.

No downloaded Python is imported, installed, tested or run. Git is used
only for object/provenance reads. Candidate source is parsed by our AST checker.
Raw third-party code, tickets and predictions are not redistributed by this repo.
"""
from collections import Counter
import csv
import hashlib
import html
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

from .archive import inspect_submission_archive
from .fileio import digest_file, read_bounded
from .historical import _read, _may_headers, evaluate_historical, may_ticket_key

CANDIDATE_REPO = 'https://github.com/saai-syvendra/hackerrank-orchestrate'
CANDIDATE_COMMIT = 'fadb4f24e36d860a9ce4d5155bb30568df80ea4b'
OFFICIAL_REPO = 'https://github.com/interviewstreet/hackerrank-orchestrate-may26'
OFFICIAL_COMMIT = 'b5a301c9e89d2f05cf4a7b04136a1399b6f3f0f4'
ARTIFACTS = {
    'problem_statement.md': '5b031a364622057cd59294f886a59df2b203b8996f9f522107cc40194e0fae9d',
    'support_tickets/support_tickets.csv': '7c862a89c5353d167a8c856aedfd12a4c799fc8bcc3b1acaabfc899c70be22e3',
    'support_tickets/sample_support_tickets.csv': 'a4a1f63fee31254e8596b7a0c464e50c995d67a8fe6e71d6aaf74d0184f38419',
    'support_tickets/output.csv': '42ee580ca5e8b9a5caa819be7d86ee026646e9035e8e82b656eaedda64d4b0fd',
}


def _git(root, *arguments):
    environment = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT') if key in os.environ}
    environment.update({'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull, 'GIT_TERMINAL_PROMPT': '0',
                        'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_NO_LAZY_FETCH': '1'})
    try:
        process = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-c', 'core.hooksPath=' + os.devnull,
                                  '-C', str(root), *arguments], capture_output=True, env=environment, timeout=30)
    except subprocess.TimeoutExpired:
        raise ValueError('Git provenance read exceeded 30 seconds') from None
    if process.returncode:
        raise ValueError('Git provenance read failed: ' + process.stderr.decode('utf-8', errors='replace')[:500])
    return process.stdout


def _verify_provenance(candidate, official):
    for root, expected in ((candidate, CANDIDATE_COMMIT), (official, OFFICIAL_COMMIT)):
        if _git(root, 'rev-parse', 'HEAD').decode().strip() != expected:
            raise ValueError(f'Calibration requires the exact pinned checkout {expected}')
    for path, expected in ARTIFACTS.items():
        if digest_file(candidate / path) != expected:
            raise ValueError('Candidate artifact differs from pinned public snapshot: ' + path)
        if path != 'support_tickets/output.csv':
            official_bytes = _git(official, 'show', OFFICIAL_COMMIT + ':' + path)
            if hashlib.sha256(official_bytes).hexdigest() != expected:
                raise ValueError('Official source artifact does not match the pinned candidate input/spec: ' + path)
    source_files = []
    for entry in _git(candidate, 'ls-tree', '-rz', 'HEAD', 'code').split(b'\0'):
        if not entry:
            continue
        metadata, name = entry.split(b'\t', 1)
        mode, kind, sha = metadata.decode().split()
        path = name.decode('utf-8')
        if kind != 'blob' or mode not in {'100644', '100755'}:
            raise ValueError('Unsupported pinned source entry: ' + path)
        content = read_bounded(candidate / path)
        actual = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        if actual != sha:
            raise ValueError('Source working copy differs from its pinned Git blob: ' + path)
        source_files.append(path)
    expected_paths = set(source_files)
    for name in source_files:
        expected_paths.update(str(parent).replace(os.sep, '/') for parent in Path(name).parents if str(parent) != '.')
    for path in (candidate / 'code').rglob('*'):
        name = str(path.relative_to(candidate)).replace(os.sep, '/')
        if path.is_symlink() or name not in expected_paths:
            raise ValueError('Unexpected/missing source paths in candidate working copy: ' + name)
    return source_files


def _write_csv(path, headers, rows):
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=headers, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def run_controls(inputs_path, headers, original_rows, destination):
    """Synthetic corruptions of saved predictions, never new ground-truth labels."""
    if len(original_rows) < 2:
        raise ValueError('Calibration controls require at least two actual output rows')
    variants = []
    variants.append(('missing_last_row', headers, [dict(row) for row in original_rows[:-1]], 'fail'))
    variants.append(('duplicate_extra_row', headers, [dict(row) for row in original_rows] + [dict(original_rows[0])], 'fail'))
    duplicate = [dict(row) for row in original_rows]
    duplicate[1] = dict(duplicate[0])
    variants.append(('duplicate_ticket_same_row_count', headers, duplicate, 'fail'))
    swapped = [dict(row) for row in original_rows]
    swapped[0], swapped[1] = swapped[1], swapped[0]
    variants.append(('swapped_input_correspondence', headers, swapped, 'fail'))
    for name, field, value in [('altered_echoed_issue', 'issue', 'Synthetic calibration mismatch'),
                               ('invalid_status', 'status', 'approved'),
                               ('blank_response', 'response', ''),
                               ('blank_justification', 'justification', '')]:
        rows = [dict(row) for row in original_rows]
        rows[0][field] = value
        variants.append((name, headers, rows, 'fail'))
    variants.append(('missing_required_request_type', [field for field in headers if field != 'request_type'], original_rows, 'fail'))
    flipped = [dict(row, status='escalated' if row['status'] == 'replied' else 'replied') for row in original_rows]
    variants.append(('valid_statuses_flipped_semantics_unknown', headers, flipped, 'unknown'))
    fabricated = [dict(row) for row in original_rows]
    fabricated[0]['response'] = 'SYNTHETIC NEGATIVE CONTROL: an unsupported policy has been invented here.'
    variants.append(('fabricated_response_semantics_unknown', headers, fabricated, 'unknown'))
    variants.append(('required_fields_only_identity_unknown', [field for field in headers if field not in {'issue', 'subject', 'company'}], original_rows, 'unknown'))
    results = []
    for name, columns, rows, expected in variants:
        path = destination / (name + '.csv')
        _write_csv(path, columns, rows)
        checks = evaluate_historical(path, {'plugin': 'may26_schema', 'input_csv': str(inputs_path)})
        failed = [check['name'] for check in checks if check['status'] == 'fail']
        unknown = [check['name'] for check in checks if check['status'] == 'unknown']
        observed = 'fail' if failed else 'unknown' if unknown else 'pass'
        results.append({'control': name, 'expected': expected, 'observed': observed, 'calibration_pass': observed == expected,
                        'failed_checks': failed, 'unknown_checks': unknown, 'mutated_output_sha256': digest_file(path)})
    return results


def validate_public(candidate_dir, official_dir, report_dir):
    candidate, official, destination = Path(candidate_dir).resolve(), Path(official_dir).resolve(), Path(report_dir)
    source_files = _verify_provenance(candidate, official)
    destination.mkdir(parents=True, exist_ok=True)
    task = {'plugin': 'may26_schema', 'profile': 'may26-public-winner-artifact-calibration-v1',
            'input_csv': str(candidate / 'support_tickets/support_tickets.csv')}
    task_path = destination / 'task.json'
    task_path.write_text(json.dumps(task, indent=2) + '\n', encoding='utf-8')
    from .cli import main
    baseline_exit = main(['evaluate', '--task', str(task_path), '--output', str(candidate / 'support_tickets/output.csv'),
                          '--source', str(candidate / 'code'), '--label', 'Saai May public saved output',
                          '--report-dir', str(destination / 'baseline')])
    baseline = json.loads((destination / 'baseline/report.json').read_text(encoding='utf-8'))
    headers, predictions = _read(candidate / 'support_tickets/output.csv')
    ih, inputs = _read(candidate / 'support_tickets/support_tickets.csv')
    _, inputs = _may_headers(ih, inputs)
    sh, samples = _read(candidate / 'support_tickets/sample_support_tickets.csv')
    _, samples = _may_headers(sh, samples)
    overlap = set(map(may_ticket_key, inputs)) & set(map(may_ticket_key, samples))
    with tempfile.TemporaryDirectory(prefix='orchestrate-public-calibration-') as temporary:
        temporary = Path(temporary)
        controls = run_controls(candidate / 'support_tickets/support_tickets.csv', headers, predictions, temporary)
        archive_path = temporary / 'reconstructed-source-only.zip'
        with zipfile.ZipFile(archive_path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name in source_files:
                archive.writestr(name, read_bounded(candidate / name))
        packaging = inspect_submission_archive(archive_path)
    report = {
        'schema_version': 1,
        'calibration_status': 'pass' if baseline_exit == 2 and packaging['status'] == 'pass' and all(control['calibration_pass'] for control in controls) else 'fail',
        'meaning': 'Tests evaluator compatibility and specified detection boundaries on real saved public artifacts. This is not an agent score or live rerun.',
        'candidate': {'repository': CANDIDATE_REPO, 'commit': CANDIDATE_COMMIT,
                      'winner_primary_source': 'https://www.linkedin.com/posts/hackerrank_ai-is-changing-what-it-means-to-be-a-developer-activity-7473306333627277312-lhfZ',
                      'artifact_identity': 'Public saved output from the May winner repository; exact identity with the submitted competition archive/run is not established.',
                      'license': 'No repository-root LICENSE found at this pin. Raw third-party code/data/predictions are not vendored or redistributed here.'},
        'official': {'repository': OFFICIAL_REPO, 'commit': OFFICIAL_COMMIT,
                     'verification': 'Candidate problem statement, input tickets and labelled samples are byte-identical to the pinned official Git objects.'},
        'artifact_sha256': ARTIFACTS,
        'source': {'tracked_code_files_verified_against_git_blobs': len(source_files),
                   'python_files_parsed': sum(name.endswith('.py') for name in source_files),
                   'executed_or_imported': False, 'checks': baseline['checks']['code']},
        'output': {'input_rows': len(inputs), 'saved_prediction_rows': len(predictions),
                   'row_correspondence': 'Row order plus echoed issue/subject/company; Unicode whitespace is collapsed, without changing words/case or answer labels.',
                   'rows_with_raw_echo_whitespace_differences': sum(any(src[key] != out[key] for key in ('issue', 'subject', 'company')) for src, out in zip(inputs, predictions)),
                   'status_distribution': dict(sorted(Counter(row['status'] for row in predictions).items())),
                   'request_type_distribution': dict(sorted(Counter(row['request_type'] for row in predictions).items())),
                   'checks': baseline['checks']['output'], 'official_score': None, 'accuracy': None},
        'label_audit': {'labelled_sample_rows': len(samples), 'sample_input_overlap': len(overlap),
                        'consequence': 'The saved 29-row output cannot be scored against the disjoint 10-row sample. No positional first-N comparison or winner-predictions-as-gold is performed.'},
        'coding_transcript': {'available': False, 'checks': baseline['checks']['coding_transcript'], 'authenticity_and_quality': 'unknown'},
        'reconstructed_packaging': dict(packaging, provenance='Built locally from the pinned public code/ files; not the original submitted ZIP.'),
        'baseline_exit_code': baseline_exit, 'baseline_status': baseline['status'],
        'controls': controls,
        'runtime': {'agent_rerun': False, 'downloaded_agent_tests_run': False, 'model_calls_made_by_this_validation': 0,
                    'original_agent_cost_tokens_latency_memory': None},
        'limitations': ['Semantic routing correctness, factual grounding, genuine coding-transcript quality and hidden accuracy remain unknown.',
                        'Schema-valid status flips and invented answer text intentionally remain unknown rather than falsely detected.',
                        'Static Python parsing and source-presence proxies do not establish engineering quality or reproduce the winner score.',
                        'June Swayam public code was considered but its current data is explicitly fake/demo and saved June predictions are absent; it is not used as genuine output calibration.']}
    (destination / 'validation.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    content = '<!doctype html><html lang="en"><meta charset="utf-8"><title>Public artifact calibration</title><h1>Public artifact calibration</h1><p>Actual saved May-winner artifacts; no live agent execution or official score.</p><pre>'
    (destination / 'validation.html').write_text(content + html.escape(json.dumps(report, indent=2)) + '</pre></html>', encoding='utf-8')
    return report
