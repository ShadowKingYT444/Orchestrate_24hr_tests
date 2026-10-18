"""Independent decision-judge audit against separately held public sample labels."""
from collections import Counter
import csv
import hashlib
import io
import json
from pathlib import Path
import re

from .calibration import identity
from .checks import read_json, strict_json
from .fileio import read_bounded

FIELDS = ('action', 'message_type')


def _metrics(rows):
    ids = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('message_id'), str) or row['message_id'] in ids:
            raise ValueError('Audit observations need unique message IDs')
        ids.add(row['message_id'])
        expected, predicted = row.get('expected'), row.get('predicted')
        if not isinstance(expected, dict) or any(not isinstance(expected.get(field), str) or not expected[field] for field in FIELDS):
            raise ValueError('Audit observations need actual target labels')
        if predicted is not None and (not isinstance(predicted, dict) or any(not isinstance(predicted.get(field), str) or not predicted[field] for field in FIELDS)):
            raise ValueError('Audit observations need typed decisions or explicit unknown')
        for field in FIELDS + ('joint',):
            correct = None if predicted is None else all(predicted[name] == expected[name] for name in FIELDS) if field == 'joint' else predicted[field] == expected[field]
            if row.get(field+'_correct') is not correct:
                raise ValueError('Recorded per-case correctness differs from the actual labels/decisions')
    reviewed = [row for row in rows if row['predicted'] is not None]
    total, count = len(rows), len(reviewed)
    unknown = total - count
    fields = {}
    for field in FIELDS + ('joint',):
        correct = sum(all(row['predicted'][name] == row['expected'][name] for name in FIELDS) if field == 'joint' else row['predicted'][field] == row['expected'][field] for row in reviewed)
        fields[field] = {'correct':correct, 'reviewed':count,
                         'accuracy_on_reviewed':correct/count if count else None,
                         'all_case_accuracy_interval':[correct/total, (correct+unknown)/total]}
        if field != 'joint':
            confusion = Counter((row['expected'][field], row['predicted'][field]) for row in reviewed)
            fields[field]['confusion'] = [{'expected':expected, 'predicted':predicted, 'count':number}
                                          for (expected, predicted), number in sorted(confusion.items())]
    return {'total_cases':total, 'reviewed_cases':count, 'unknown_cases':unknown, 'fields':fields}


def audit_labels(labels_csv, predictions_path, protocol_path, destination, input_pack=None):
    protocol = read_json(protocol_path)
    if not isinstance(protocol, dict) or protocol.get('protocol_version') != 'official-labelled-sample-audit-v1' or protocol.get('protocol_sha256') != identity(protocol, 'protocol_sha256'):
        raise ValueError('Label audit requires the frozen, identity-checked audit protocol')
    if not isinstance(protocol.get('sample_size'), int) or isinstance(protocol['sample_size'], bool) or not 1 <= protocol['sample_size'] <= 200:
        raise ValueError('Bounded audit sample size must be1..200')
    # Freeze prediction identity before reading the separately held label file.
    prediction_raw = read_bounded(predictions_path)
    prediction_sha = hashlib.sha256(prediction_raw).hexdigest()
    prediction = strict_json(prediction_raw.decode('utf-8'))
    if not isinstance(prediction, dict) or prediction.get('protocol_sha256') != protocol['protocol_sha256']:
        raise ValueError('Independent predictions must bind the predeclared audit protocol')
    if not isinstance(prediction.get('input_pack_sha256'), str) or re.fullmatch('[0-9a-f]{64}', prediction['input_pack_sha256']) is None:
        raise ValueError('Independent predictions need the label-free input pack hash')
    if input_pack is not None and hashlib.sha256(read_bounded(input_pack)).hexdigest() != prediction['input_pack_sha256']:
        raise ValueError('Supplied input pack differs from the independent prediction snapshot')
    cases = prediction.get('predictions')
    if not isinstance(cases, list) or not cases:
        raise ValueError('Independent audit predictions must be a nonempty list')
    by_id = {}
    for case in cases:
        if not isinstance(case, dict) or not isinstance(case.get('message_id'), str) or not case['message_id'] or case['message_id'] in by_id:
            raise ValueError('Audit prediction IDs must be unique nonempty strings')
        if case.get('review_status') == 'unknown':
            if any(case.get(field) is not None for field in FIELDS) or not isinstance(case.get('unknown_reason'), str) or not case['unknown_reason'].strip():
                raise ValueError('Unknown audit decisions need an evidence limitation, not forced labels')
        elif any(not isinstance(case.get(field), str) or not case[field].strip() for field in FIELDS):
            raise ValueError('Reviewed audit predictions require action and message_type strings')
        by_id[case['message_id']] = case
    label_raw = read_bounded(labels_csv)
    if hashlib.sha256(label_raw).hexdigest() != protocol.get('sample_csv_sha256'):
        raise ValueError('Sample label file differs from the predeclared official snapshot')
    reader = csv.DictReader(io.StringIO(label_raw.decode('utf-8-sig')))
    if not reader.fieldnames or any(field not in reader.fieldnames for field in ('message_id',) + FIELDS) or len(reader.fieldnames) != len(set(reader.fieldnames)):
        raise ValueError('Official sample needs unique headers including message_id/action/message_type')
    labels = list(reader)
    ids = [row['message_id'] for row in labels]
    if len(labels) != protocol.get('sample_size') or len(ids) != len(set(ids)) or set(ids) != set(by_id):
        raise ValueError('Audit prediction IDs must exactly align with all official sample IDs')
    rows = []
    for label in labels:
        case = by_id[label['message_id']]
        expected = {field:label[field] for field in FIELDS}
        if any(not value for value in expected.values()):
            raise ValueError('Official sample target labels must be present')
        predicted = None if case.get('review_status') == 'unknown' else {field:case[field] for field in FIELDS}
        row = {'message_id':label['message_id'], 'expected':expected, 'predicted':predicted,
               'unknown_reason':case.get('unknown_reason') if predicted is None else None}
        for field in FIELDS:
            row[field+'_correct'] = predicted[field] == expected[field] if predicted is not None else None
        row['joint_correct'] = all(row[field+'_correct'] for field in FIELDS) if predicted is not None else None
        rows.append(row)
    report = {'schema_version':1, 'kind':'official_sample_decision_judge_audit',
              'protocol_sha256':protocol['protocol_sha256'], 'predictions_sha256':prediction_sha,
              'input_pack_sha256':prediction['input_pack_sha256'],
              'input_pack_hash_verified':input_pack is not None,
              'sample_csv_sha256':hashlib.sha256(label_raw).hexdigest(),
              'rows':rows, 'metrics':_metrics(rows),
              'scope':'Independent judge action/type decisions on a public development sample. No candidate execution, official category-point prediction, final-output accuracy or open-text semantic validation.',
              'limits':protocol['limits']}
    report['report_sha256'] = identity(report, 'report_sha256')
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    existing = target/'label-audit.json'
    if existing.exists() and read_bounded(existing) != (json.dumps(report,indent=2)+'\n').encode():
        raise ValueError('Choose a new audit report directory; prior results are not overwritten')
    existing.write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    (target/'predictions-frozen.json').write_bytes(prediction_raw)
    lines = ['# Official public-sample decision-judge audit', '', report['scope'], '',
             f"Coverage: {report['metrics']['reviewed_cases']}/{report['metrics']['total_cases']} reviewed; {report['metrics']['unknown_cases']} unknown.", '',
             '| Field | Correct / reviewed | Accuracy on reviewed | All-case missing-decision interval |', '|---|---:|---:|---:|']
    for field, result in report['metrics']['fields'].items():
        low, high = result['all_case_accuracy_interval']
        accuracy = f"{result['accuracy_on_reviewed']:.2%}" if result['accuracy_on_reviewed'] is not None else 'Unknown'
        lines.append(f"| {field} | {result['correct']}/{result['reviewed']} | {accuracy} | {low:.2%}–{high:.2%} |")
    lines += ['', 'Intervals cover missing decisions only, not statistical uncertainty. Do not convert this sample accuracy into official /30 output points.']
    (target/'label-audit.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report


def verify_audit(report, predictions_path):
    if not isinstance(report, dict) or report.get('report_sha256') != identity(report, 'report_sha256'):
        raise ValueError('Frozen audit report identity mismatch')
    prediction_raw = read_bounded(predictions_path)
    if hashlib.sha256(prediction_raw).hexdigest() != report.get('predictions_sha256'):
        raise ValueError('Independent predictions changed after audit freeze')
    rows = report.get('rows')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Audit replay requires recorded per-case observations')
    if _metrics(rows) != report.get('metrics'):
        raise ValueError('Audit totals differ from recorded per-case comparisons')
    predictions = strict_json(prediction_raw.decode('utf-8'))
    items = predictions.get('predictions') if isinstance(predictions, dict) else None
    if not isinstance(items, list) or len(items) != len(rows) or any(not isinstance(item, dict) or not isinstance(item.get('message_id'), str) for item in items):
        raise ValueError('Audit replay needs the original per-case predictions')
    if any(predictions.get(key) != report.get(key) for key in ('protocol_sha256','input_pack_sha256')):
        raise ValueError('Audit metadata differs from the frozen prediction protocol/input snapshot')
    by_id = {item['message_id']:item for item in items}
    if len(by_id) != len(items) or set(by_id) != {row['message_id'] for row in rows}:
        raise ValueError('Frozen audit prediction IDs changed')
    for row in rows:
        item = by_id[row['message_id']]
        predicted = None if item.get('review_status') == 'unknown' else {field:item.get(field) for field in FIELDS}
        if predicted != row['predicted']:
            raise ValueError('Audit observation does not match the frozen independent prediction')
    return report['metrics']
