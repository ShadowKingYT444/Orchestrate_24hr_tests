"""Frozen evidence reviews and honest local-versus-official comparison.

No offsets, model calls, candidate execution or missing-category zero filling.
Hashes bind supplied evidence, not its equivalence to a contest server upload.
"""
import hashlib
import json
import math
from pathlib import Path
import re

from .checks import read_json, strict_json
from .fileio import read_bounded
from .judging import (export_bundle, import_review, validate_bundle, RUBRICS,
                      LEGACY_RUBRICS, RUBRIC_VERSION, LEGACY_RUBRIC_VERSION)

AUGUST_WEIGHTS = {'action':35, 'message_type':20, 'reason':25, 'evidence_relevance':15, 'confidence_reasonableness':5}
AUGUST_CAPS = {'unsafe_notify':25, 'contradicted_or_invented_reasoning':50, 'irrelevant_or_generic_reason':70}
MAY_WEIGHTS = {'status':25, 'product_area':10, 'request_type':10, 'response':35, 'justification':20}
MAY_CAP_POLICY = 'Preserve original local cap: genuinely deficient or contradictory justification caps the whole reviewed row at70; safety findings remain explicit, not a reconstructed official safety aggregation.'
BASE_PROTOCOL = 'published-rubric-study-v1'
AUGUST_PROTOCOL = 'published-rubric-study-v1-august-output-amendment'


def identity(value, field):
    body = dict(value)
    body.pop(field, None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def load_protocol(path):
    return _validate_protocol(read_json(path))


def _validate_protocol(value):
    if not isinstance(value, dict) or value.get('protocol_sha256') != identity(value, 'protocol_sha256'):
        raise ValueError('Calibration protocol identity mismatch')
    if value.get('rubric_version') != RUBRIC_VERSION:
        raise ValueError('This implementation requires the explicit published-aid-v2 rubric')
    if value.get('protocol_version') not in (BASE_PROTOCOL, AUGUST_PROTOCOL):
        raise ValueError('Unsupported calibration protocol profile; implement/version the new method explicitly')
    for key, category in (('code_criteria', 'code'), ('transcript_criteria', 'coding_transcript')):
        criteria = value.get(key)
        if not isinstance(criteria, dict) or any(not isinstance(item, dict) for item in criteria.values()):
            raise ValueError('Protocol criteria must map names to criterion objects')
        weights = {name: item.get('weight') for name, item in criteria.items()}
        if weights != RUBRICS[category]:
            raise ValueError('Protocol criterion weights differ from the supported frozen rubric')
    if value.get('category_weights') != {'code': 30, 'output': 30, 'coding_transcript': 10}:
        raise ValueError('Category-weight override needs an explicitly implemented/versioned edition profile')
    methods = value.get('output_protocol')
    if not isinstance(methods, dict):
        raise ValueError('Protocol requires explicit supported output methods')
    may = methods.get('may_support_saved_answers')
    if not isinstance(may, dict) or may.get('field_weights_local') != MAY_WEIGHTS or may.get('row_rating_anchors') != [0,25,50,75,100] or may.get('justification_policy') != MAY_CAP_POLICY:
        raise ValueError('May output protocol differs from the preserved implemented weights/cap/scale')
    august = methods.get('august_routing_saved_answers')
    if value['protocol_version'] == AUGUST_PROTOCOL:
        if not isinstance(august, dict) or august.get('field_weights_local') != AUGUST_WEIGHTS or august.get('caps_local') != AUGUST_CAPS or august.get('rating_anchors') != [0,1,2,3,4]:
            raise ValueError('August output protocol differs from implemented frozen weights/caps/scale')
    elif not isinstance(august, str):
        raise ValueError('Base protocol does not implement the later August output method')
    return value


def export_calibration_bundle(source, destination, protocol_path, edition, transcript=None):
    protocol = load_protocol(protocol_path)
    if edition not in ('may26', 'august26'):
        raise ValueError('Select an implemented edition context; verify October overrides before adding one')
    target = Path(destination)
    if target.exists():
        raise ValueError('Choose a new calibration bundle path; frozen evidence is never overwritten')
    # A temporary sibling avoids leaving an unannotated bundle on validation error.
    temporary = target.with_name(target.name + '.pending')
    if temporary.exists():
        raise ValueError('Pending export path already exists')
    try:
        bundle = export_bundle(source, temporary, transcript)
        bundle.update(calibration_protocol=protocol, edition=edition, calibration_bundle_version=1)
        bundle.pop('bundle_id')
        bundle['bundle_id'] = hashlib.sha256(json.dumps(bundle, sort_keys=True).encode()).hexdigest()
        serialized = json.dumps(bundle, indent=2) + '\n'
        if len(serialized.encode()) > 5_000_000:
            raise ValueError('Protocol-bound calibration bundle exceeds5MB')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(serialized, encoding='utf-8')
        return bundle
    finally:
        if temporary.exists():
            temporary.unlink()


def freeze_review(bundle_path, review_path, destination, preserve_legacy=False):
    bundle, review = read_json(bundle_path), read_json(review_path)
    accepted = import_review(bundle, review)
    legacy = accepted['rubric_version'] == LEGACY_RUBRIC_VERSION
    protocol = bundle.get('calibration_protocol')
    if legacy:
        if not preserve_legacy:
            raise ValueError('Original legacy review needs explicit --preserve-legacy')
    else:
        _validate_protocol(protocol)
        if review.get('calibration_protocol_sha256') != protocol['protocol_sha256']:
            raise ValueError('New review must bind the frozen calibration protocol')
        for entries in review['categories'].values():
            if entries is not None and not isinstance(entries, dict):
                raise ValueError('Review categories must be criterion objects or null')
            for entry in (entries or {}).values():
                if not math.isclose(entry['score'] / 5, round(entry['score'] / 5)):
                    raise ValueError('Predeclared new criterion ratings use5-point steps')
    artifact = {'schema_version': 1, 'kind': 'frozen_evidence_review',
                'rubric_version': accepted['rubric_version'], 'bundle_id': bundle['bundle_id'],
                'protocol_sha256': protocol['protocol_sha256'] if protocol else None,
                'edition': bundle.get('edition'), 'preserved_original': legacy,
                'review': review, 'category_scores_100': accepted['category_scores'],
                'source_manifest': [{'source': item['source'], 'sha256': item['sha256'],
                                     'line_count': len(item['text'].splitlines())}
                                    for item in bundle['untrusted_evidence_files']],
                'evidence_verification': 'Exact quotes/line ranges and source hashes checked against the supplied full bundle at freeze time; no server-upload identity or authenticity attestation.'}
    artifact['artifact_sha256'] = identity(artifact, 'artifact_sha256')
    target = Path(destination)
    if target.exists():
        raise ValueError('Choose a new review path; original judgments are never overwritten')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(artifact, indent=2) + '\n', encoding='utf-8')
    return artifact


def _rating(value, maximum):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value <= maximum or not math.isfinite(value):
        raise ValueError('Review ratings must be finite numbers within their declared scale')
    return value


def validate_frozen(artifact, bundle=None):
    if not isinstance(artifact, dict) or artifact.get('artifact_sha256') != identity(artifact, 'artifact_sha256'):
        raise ValueError('Frozen review identity mismatch')
    version = artifact.get('rubric_version')
    rubrics = RUBRICS if version == RUBRIC_VERSION else LEGACY_RUBRICS if version == LEGACY_RUBRIC_VERSION else None
    if rubrics is None:
        raise ValueError('Unsupported frozen review rubric')
    review = artifact.get('review', {})
    if not isinstance(review, dict):
        raise ValueError('Frozen review body must be an object')
    if review.get('bundle_id') != artifact.get('bundle_id'):
        raise ValueError('Frozen review/bundle identity mismatch')
    if version == RUBRIC_VERSION and review.get('calibration_protocol_sha256') != artifact.get('protocol_sha256'):
        raise ValueError('Frozen review/protocol identity mismatch')
    categories = review.get('categories')
    if not isinstance(categories, dict) or set(categories) - set(rubrics):
        raise ValueError('Malformed frozen review categories')
    scores = {}
    for category, weights in rubrics.items():
        entries = categories.get(category)
        if entries is None:
            scores[category] = None
            continue
        if not isinstance(entries, dict) or set(entries) != set(weights):
            raise ValueError('Frozen review requires every declared criterion')
        if any(not isinstance(entry, dict) for entry in entries.values()):
            raise ValueError('Criterion entries must be objects')
        scores[category] = round(sum(_rating(entries[name].get('score'), 100) * weight / 100
                                     for name, weight in weights.items()), 4)
    if scores != artifact.get('category_scores_100'):
        raise ValueError('Stored review aggregate differs from criterion arithmetic')
    if bundle is not None:
        validate_bundle(bundle)
        accepted = import_review(bundle, review)
        actual = [{'source': item['source'], 'sha256': item['sha256'],
                   'line_count': len(item['text'].splitlines())} for item in bundle['untrusted_evidence_files']]
        if actual != artifact.get('source_manifest') or accepted['category_scores'] != scores:
            raise ValueError('Reprovided evidence differs from the frozen review')
        protocol = bundle.get('calibration_protocol')
        if protocol and protocol.get('protocol_sha256') != artifact.get('protocol_sha256'):
            raise ValueError('Reprovided bundle uses a different study protocol')
    return scores


def _local_file(root, reference):
    if not isinstance(reference, str):
        raise ValueError('Calibration artifact path must be relative text')
    path = (root / reference).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Calibration artifact path escapes the dataset directory')
    return path


def output_estimate(review, weight, protocol=None):
    """Recompute preserved May or partial August qualitative review arithmetic."""
    if 'case_reviews' not in review or not isinstance(review['case_reviews'], list) or not review['case_reviews']:
        raise ValueError('Saved-output review needs actual per-case judgments')
    if review.get('review_kind') == 'august_partial_grounded':
        if protocol is not None:
            _validate_protocol(protocol)
            if protocol['protocol_version'] != AUGUST_PROTOCOL or review.get('protocol_sha256') != protocol['protocol_sha256']:
                raise ValueError('August output review must bind the method-bearing amendment, not the base protocol')
        weights = AUGUST_WEIGHTS
        total = review.get('total_case_count')
        if not isinstance(total, int) or isinstance(total, bool) or total != len(review['case_reviews']):
            raise ValueError('Partial output review must retain every case, including unknowns')
        hashes = review.get('source_hashes')
        if not isinstance(hashes, dict) or not hashes or any(not isinstance(key, str) or not key or not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None for key, value in hashes.items()):
            raise ValueError('Grounded output review needs a valid frozen source-hash manifest')
    else:
        weights = MAY_WEIGHTS
        total = len(review['case_reviews'])
    if review.get('local_field_weights') != weights:
        raise ValueError('Output field weights differ from the predeclared local method')
    values, seen = [], set()
    for case in review['case_reviews']:
        if not isinstance(case, dict):
            raise ValueError('Output review cases must be objects')
        identifier = case.get('message_id', case.get('row'))
        if identifier is None or not isinstance(identifier, (str, int)) or isinstance(identifier, bool) or identifier in seen:
            raise ValueError('Output review case IDs must be unique')
        seen.add(identifier)
        ratings = case.get('ratings_0_to_4')
        if ratings is None and case.get('review_status') == 'unknown':
            if not isinstance(case.get('unknown_reason'), str) or not case['unknown_reason'].strip():
                raise ValueError('Unknown output case needs an explicit evidence limitation')
            continue
        if not isinstance(ratings, dict) or set(ratings) != set(weights):
            raise ValueError('Reviewed output cases need every declared field rating')
        if 'justification' not in ratings and any(_rating(value, 4) != int(value) for value in ratings.values()):
            raise ValueError('Frozen August output ratings use integer0..4 anchors')
        if not isinstance(case.get('rationale'), str) or len(case['rationale'].strip()) < 20:
            raise ValueError('Reviewed output case needs a specific semantic rationale')
        references = case.get('evidence_refs') if 'justification' not in ratings else case.get('evidence_ids')
        if not isinstance(references, list) or not references:
            raise ValueError('Reviewed output case needs actual context/corpus evidence references')
        if 'justification' not in ratings:
            for reference in references:
                if not isinstance(reference, dict) or not isinstance(reference.get('source_file'), str) or not isinstance(reference.get('record_key'), str) or not reference['record_key'].strip():
                    raise ValueError('Grounded evidence needs source_file and record_key strings')
                source = reference['source_file']
                if source not in hashes or reference.get('sha256') != hashes[source]:
                    raise ValueError('Output evidence reference differs from frozen source hash')
        else:
            sources = review.get('sources', {})
            if not isinstance(sources, dict) or any(not isinstance(name, str) or name not in sources or not isinstance(sources[name], dict) or not isinstance(sources[name].get('sha256'), str) or re.fullmatch('[0-9a-f]{64}', sources[name]['sha256']) is None for name in references):
                raise ValueError('Preserved corpus evidence IDs must name hashed sources')
        score = sum(_rating(ratings[name], 4) / 4 * amount for name, amount in weights.items())
        if 'justification' in ratings:
            score = min(score, 70 if ratings['justification'] <= 1 else 100)
        else:
            flags = case.get('flags', {})
            if not isinstance(flags, dict):
                raise ValueError('Semantic cap flags must be an object')
            names = ('unsafe_notify', 'contradicted_or_invented_reasoning', 'irrelevant_or_generic_reason')
            if any(not isinstance(flags.get(name), bool) for name in names):
                raise ValueError('August semantic caps require explicit flags')
            for name, cap in AUGUST_CAPS.items():
                if flags[name]:
                    score = min(score, cap)
        values.append(score)
    unknown = total - len(values)
    lower = sum(values) / total * weight / 100
    upper = (sum(values) + unknown * 100) / total * weight / 100
    return {'points': round(lower, 8) if not unknown else None,
            'reviewed_mean_points': round(sum(values) / len(values) * weight / 100, 8) if values else None,
            'whole_output_interval': [round(lower, 8), round(upper, 8)],
            'reviewed_cases': len(values), 'unknown_cases': unknown, 'total_cases': total,
            'method': 'LOCAL corpus/context-grounded judgments, not private-gold accuracy'}


def calibration_report(dataset_path, destination):
    dataset_path = Path(dataset_path).resolve()
    dataset_raw = read_bounded(dataset_path)
    dataset = strict_json(dataset_raw.decode('utf-8'))
    if not isinstance(dataset, dict) or dataset.get('schema_version') != 1 or not isinstance(dataset.get('cases'), list) or not 1 <= len(dataset['cases']) <= 1000:
        raise ValueError('Calibration dataset must declare schema_version1 and cases')
    if dataset.get('targets_known_before_protocol') is not True:
        raise ValueError('This selected public study must disclose prior target knowledge; no blind-holdout claim')
    root = dataset_path.parent
    protocols = {}
    if not isinstance(dataset.get('protocols'), list):
        raise ValueError('Calibration protocols must be a list of references')
    for reference in dataset['protocols']:
        if not isinstance(reference, dict):
            raise ValueError('Protocol references must be objects')
        protocol = load_protocol(_local_file(root, reference['path']))
        if protocol['protocol_sha256'] != reference.get('protocol_sha256'):
            raise ValueError('Dataset protocol differs from its frozen reference')
        protocols[protocol['protocol_sha256']] = protocol
    if not protocols:
        raise ValueError('Calibration dataset must identify its frozen protocols')
    observations = None
    if dataset.get('official_observations'):
        reference = dataset['official_observations']
        path = _local_file(root, reference['path'])
        raw = read_bounded(path)
        if hashlib.sha256(raw).hexdigest() != reference.get('sha256'):
            raise ValueError('Official observation file changed after dataset freeze')
        payload = strict_json(raw.decode('utf-8'))
        observations = payload.get('records') if isinstance(payload, dict) else None
        if not isinstance(observations, dict):
            raise ValueError('Official observations require separately recorded target records')
    rows, ids = [], set()
    for case in dataset['cases']:
        if not isinstance(case, dict):
            raise ValueError('Calibration cases must be objects')
        identifier = case.get('id')
        if not isinstance(identifier, str) or identifier in ids or case.get('role') not in ('development', 'external_exploratory', 'context_only'):
            raise ValueError('Unique case ID and honest study role required')
        ids.add(identifier)
        official = case.get('official_points')
        if not isinstance(official, dict) or not isinstance(case.get('official_source_url'), str):
            raise ValueError('Official category targets need separately recorded primary provenance')
        if any(not isinstance(case.get(stage, {}), dict) for stage in ('before', 'after')):
            raise ValueError('Before/after evidence stages must be objects')
        if not isinstance(case.get('evidence_coverage', {}), dict):
            raise ValueError('Category evidence coverage must be an object')
        if observations is not None:
            observation = observations.get(identifier)
            if not isinstance(observation, dict) or observation.get('official_points') != official or observation.get('source_url') != case['official_source_url']:
                raise ValueError('Dataset official targets differ from separately frozen observations')
        for category, weight in (('code', 30), ('output', 30), ('coding_transcript', 10)):
            target = _rating(official[category], weight) if official.get(category) is not None else None
            row = {'case_id': identifier, 'role': case['role'], 'edition': case.get('edition'),
                   'category': category, 'maximum': weight, 'official_points': target,
                   'candidate_commit':case.get('candidate_commit'), 'official_source_url':case['official_source_url'],
                   'evidence_coverage':case.get('evidence_coverage', {}).get(category),
                   'artifact_correspondence': case.get('artifact_correspondence'),
                   'before': None, 'after': None}
            for stage in ('before', 'after'):
                reference = case.get(stage, {}).get(category)
                if reference is None:
                    continue
                if not isinstance(reference, dict):
                    raise ValueError('Stage evidence references must be objects')
                path = _local_file(root, reference['path'])
                raw = read_bounded(path)
                if hashlib.sha256(raw).hexdigest() != reference.get('sha256'):
                    raise ValueError('Calibration review file changed after dataset freeze')
                review = strict_json(raw.decode('utf-8'))
                if reference.get('kind') == 'frozen_rubric_review':
                    scores = validate_frozen(review)
                    if review.get('protocol_sha256') not in protocols and not review.get('preserved_original'):
                        raise ValueError('New review is not bound to a dataset protocol')
                    value = scores[category]
                    estimate = {'points': round(value * weight / 100, 8) if value is not None else None,
                                'rubric_version': review['rubric_version'], 'protocol_sha256': review.get('protocol_sha256'),
                                'source_check': 'Frozen hash/criterion math verified; use calibration verify with original bundle to recheck exact quotes.'}
                elif reference.get('kind') == 'saved_output_review' and category == 'output':
                    if review.get('protocol_sha256') not in protocols and reference.get('preserved_existing') is not True:
                        raise ValueError('New output review must bind a dataset protocol')
                    method = protocols.get(review.get('protocol_sha256'))
                    if review.get('review_kind') == 'august_partial_grounded' and method is None:
                        raise ValueError('August output method cannot be bypassed as an unbound preserved review')
                    estimate = output_estimate(review, weight, method)
                else:
                    raise ValueError('Unsupported calibration stage evidence kind')
                if reference.get('revision'):
                    estimate['revision'] = reference['revision']
                points = estimate['points']
                if target is not None and points is not None:
                    estimate.update(signed_gap=round(points-target, 8), absolute_gap=round(abs(points-target), 8))
                elif target is not None and estimate.get('whole_output_interval'):
                    gaps = [round(value-target, 8) for value in estimate['whole_output_interval']]
                    estimate['signed_gap_interval'] = gaps
                    estimate['absolute_gap_interval'] = [0 if gaps[0] <= 0 <= gaps[1] else min(abs(value) for value in gaps), max(abs(value) for value in gaps)]
                row[stage] = estimate
            rows.append(row)
    report = {'schema_version':1, 'dataset_sha256':hashlib.sha256(dataset_raw).hexdigest(),
              'protocol_sha256':sorted(protocols),
              'study':dataset.get('study'), 'targets_known_before_protocol':True, 'rows':rows,
              'limits':dataset.get('limitations'), 'numeric_fit_applied':False,
              'interpretation':'Observed differences between assessments. Not matched-upload prediction errors, a truly blind holdout, statistical calibration, or cross-edition ranking validation.'}
    folder = Path(destination)
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'calibration.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    lines = ['# Frozen calibration comparison', '', report['interpretation'], '',
             '| Case | Category | Official | Original local | After frozen protocol | Original absolute gap | After absolute gap |',
             '|---|---|---:|---:|---:|---:|---:|']
    def cell(estimate):
        if estimate is None:
            return 'Unknown / not reviewed'
        if estimate.get('points') is not None:
            return f"{estimate['points']:.4f}" + (' (unchanged)' if estimate.get('revision') else '')
        if estimate.get('whole_output_interval'):
            low, high = estimate['whole_output_interval']
            return f'Unknown; contribution interval {low:.4f}–{high:.4f}'
        return 'Unknown'
    for row in rows:
        def gap_cell(estimate):
            estimate = estimate or {}
            if 'absolute_gap' in estimate:
                return f"{estimate['absolute_gap']:.4f}"
            if 'absolute_gap_interval' in estimate:
                low, high = estimate['absolute_gap_interval']
                return f'{low:.4f}–{high:.4f} (interval)'
            return 'Not calculable'
        label = row['case_id'].replace('|', '\\|').replace('\n', ' ')
        lines.append(f"| {label} | {row['category']} /{row['maximum']} | {row['official_points']} | {cell(row['before'])} | {cell(row['after'])} | {gap_cell(row['before'])} | {gap_cell(row['after'])} |")
    lines += ['', 'Unknown is not zero. Intervals cover missing row contributions only, not statistical uncertainty or expected official-score coverage.', '', 'No offset, rescaling or target-aware score fitting is applied.']
    lines += ['', '## Evidence and interpretation limits', '']
    for case in dataset['cases']:
        label = case['id'].replace('\n', ' ').replace('|', '\\|')
        lines.append('- '+label+': '+str(case.get('artifact_correspondence','Not established')).replace('\n',' '))
    for limitation in dataset.get('limitations', []):
        lines.append('- '+str(limitation).replace('\n',' '))
    (folder/'calibration.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report
