"""Offline schema checks for historical contests; no official fixtures or scoring.

Sources: https://raw.githubusercontent.com/interviewstreet/hackerrank-orchestrate-june26/main/problem_statement.md
https://raw.githubusercontent.com/interviewstreet/hackerrank-orchestrate-september26/main/problem_statement.md
These checks do not assess images, affordability reasoning, or hidden-test success.
"""
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation, DecimalException, localcontext
import io
import json
from pathlib import Path
import re

from .checks import result
from .fileio import read_bounded

MAX_CSV = 5_000_000
JUNE_HEADERS = 'user_id,image_paths,user_claim,claim_object,evidence_standard_met,evidence_standard_met_reason,risk_flags,issue_type,object_part,claim_status,claim_status_justification,supporting_image_ids,valid_image,severity'.split(',')
MAY_REQUIRED = ['status', 'product_area', 'response', 'justification', 'request_type']
SEPTEMBER_HEADERS = 'request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation'.split(',')
PARTS = {
    'car': set('front_bumper rear_bumper door hood windshield side_mirror headlight taillight fender quarter_panel body unknown'.split()),
    'laptop': set('screen keyboard trackpad hinge lid corner port base body unknown'.split()),
    'package': set('box package_corner package_side seal label contents item unknown'.split()),
}
ISSUES = set('dent scratch crack glass_shatter broken_part missing_part torn_packaging crushed_packaging water_damage stain none unknown'.split())
FLAGS = set('none blurry_image cropped_or_obstructed low_light_or_glare wrong_angle wrong_object wrong_object_part damage_not_visible claim_mismatch possible_manipulation non_original_image text_instruction_present user_history_risk manual_review_required'.split())


def _read(path):
    raw = read_bounded(path, MAX_CSV)
    rows = []
    for row in csv.reader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True):
        if len(rows) >= 50_001 or len(row) > 256:
            raise ValueError('CSV exceeds the local limit of 50,000 data rows or 256 columns')
        rows.append(row)
    if not rows or not rows[0] or len(set(rows[0])) != len(rows[0]):
        raise ValueError('CSV needs a nonempty, unique header')
    if any(len(r) != len(rows[0]) for r in rows[1:]):
        raise ValueError('CSV contains a row with the wrong number of fields')
    return rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]


def _check(name, errors):
    return result(name, 'fail' if errors else 'pass', errors[:50] or ['All supplied rows satisfy this check'])


def _decimal(value):
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError('invalid decimal') from None
    if not number.is_finite():
        raise ValueError('non-finite decimal')
    if len(number.as_tuple().digits) > 100 or abs(number.as_tuple().exponent) > 1000:
        raise ValueError('decimal exceeds local 100-digit / exponent +/-1000 limit')
    return number


def _remainder(requested, safe):
    # Exact for every value admitted by _decimal; default Decimal precision is
    # only 28 and can otherwise silently round a small remainder difference.
    with localcontext() as context:
        context.prec = 2200
        return requested - safe


def _date(value):
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('date must be YYYY-MM-DD')
    return dt.date.fromisoformat(value)


def _stems(value):
    """Recognize only unambiguous encodings; do not guess unknown delimiters."""
    if value.startswith('['):
        try:
            paths = json.loads(value)
        except ValueError:
            return None
        if not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths):
            return None
    elif ';' in value:
        paths = value.split(';')
    elif '|' in value:
        paths = value.split('|')
    elif ',' in value or '\n' in value or not value:
        return None
    else:
        paths = [value]
    return {Path(p.strip()).stem for p in paths}


def _may_headers(headers, rows):
    """The May sample uses title case/spaces; no output order is mandated."""
    normalized = [name.strip().casefold().replace(' ', '_') for name in headers]
    if len(normalized) != len(set(normalized)):
        raise ValueError('May headers contain ambiguous normalized aliases')
    return normalized, [{new: row[old] for old, new in zip(headers, normalized)} for row in rows]


def may_ticket_key(row):
    """Declared lexical normalization only; never semantic/label normalization."""
    return tuple(' '.join(row.get(name, '').split()) for name in ('issue', 'subject', 'company'))


def _may(inputs, outputs, echoed):
    count, identity, enums, text = [], [], [], []
    if len(inputs) != len(outputs):
        count.append(f'Expected {len(inputs)} rows; received {len(outputs)}. Duplicate input tickets must be preserved.')
    for index, (src, out) in enumerate(zip(inputs, outputs), 2):
        if echoed and may_ticket_key(src) != may_ticket_key(out):
            identity.append(f'Row {index}: echoed issue/subject/company differs from the corresponding input after whitespace collapse')
    for index, row in enumerate(outputs, 2):
        if row['status'] not in {'replied', 'escalated'}:
            enums.append(f'Row {index}: invalid status')
        if row['request_type'] not in {'product_issue', 'feature_request', 'bug', 'invalid'}:
            enums.append(f'Row {index}: invalid request_type')
        if not row['response'].strip() or not row['justification'].strip():
            text.append(f'Row {index}: response and justification must be nonempty for this local readiness check')
    return [_check('May input row count', count),
            _check('May echoed input identity', identity) if echoed else result('May echoed input identity', 'unknown', ['No complete issue/subject/company echo; row count alone cannot verify input-to-output correspondence']),
            _check('May categorical fields', enums), _check('May nonempty response and justification', text),
            result('May routing and response semantics', 'unknown', ['This schema checker does not compare independent labels. Schema checks cannot establish correct escalation, corpus grounding, justification quality, safety, or hidden accuracy. Product area has no published fixed enum; no slug convention is imposed.'])]


def _june(inputs, outputs):
    coverage = []
    if len(inputs) != len(outputs):
        coverage.append('Output row count differs from input; duplicate input rows must be preserved')
    for i, (src, out) in enumerate(zip(inputs, outputs), 2):
        if any(src[k] != out[k] for k in JUNE_HEADERS[:4]):
            coverage.append(f'Row {i}: first four fields differ from the corresponding input row')
    enums, support, ambiguous, reasons = [], [], [], []
    values = {'claim_object': set(PARTS), 'evidence_standard_met': {'true', 'false'},
              'valid_image': {'true', 'false'}, 'claim_status': {'supported', 'contradicted', 'not_enough_information'},
              'severity': {'none', 'low', 'medium', 'high', 'unknown'}, 'issue_type': ISSUES}
    for i, row in enumerate(outputs, 2):
        if not row['evidence_standard_met_reason'].strip() or not row['claim_status_justification'].strip():
            reasons.append(f'Row {i}: evidence and claim decisions require nonempty reasons')
        for key, allowed in values.items():
            if row[key] not in allowed:
                enums.append(f'Row {i}: invalid {key}')
        if row['object_part'] not in PARTS.get(row['claim_object'], set()):
            enums.append(f'Row {i}: object_part does not belong to claim_object')
        flags = row['risk_flags'].split(';')
        if any(f not in FLAGS for f in flags) or ('none' in flags and len(flags) > 1):
            enums.append(f'Row {i}: invalid risk_flags list')
        if row['supporting_image_ids'] == 'none':
            continue
        stems = _stems(row['image_paths'])
        ids = row['supporting_image_ids'].split(';')
        if stems is None or any(',' in x or '|' in x for x in ids):
            ambiguous.append(f'Row {i}: image path or supporting ID delimiter is not recognized')
        elif not all(x and x in stems for x in ids):
            support.append(f'Row {i}: supporting image ID is not an input filename stem')
    checks = [_check('June input rows preserved', coverage), _check('June categorical fields', enums), _check('June supporting image references', support), _check('June nonempty decision reasons', reasons)]
    if ambiguous:
        checks.append(result('June ambiguous image reference encoding', 'unknown', ambiguous[:50]))
    checks.append(result('June image and claim semantics', 'unknown', ['Requires image evidence and independent adjudication; schema checks cannot establish claim correctness']))
    return checks


def _september(inputs, outputs):
    errors, amounts, dates, plans, changes, explanations = [], [], [], [], [], []
    source = {r['request_id']: r for r in inputs}
    ids = [r['request_id'] for r in outputs]
    input_ids = [r['request_id'] for r in inputs]
    if not all(input_ids) or len(source) != len(inputs):
        errors.append('Input request IDs must be nonempty and unique')
    if not all(ids) or len(set(ids)) != len(ids) or set(ids) != set(source):
        errors.append('Output must contain each input request ID exactly once and no other IDs')
    enums = []
    for i, row in enumerate(outputs, 2):
        if not row['decision_explanation'].strip():
            explanations.append(f'Row {i}: decision_explanation must be nonempty')
        try:
            if row['spending_changes_needed'] != 'none':
                entries = row['spending_changes_needed'].split('|')
                if not 1 <= len(entries) <= 3:
                    raise ValueError('expected at most three changes')
                seen = set()
                for item in entries:
                    parts = item.split(':')
                    if len(parts) not in (2, 3) or not parts[1].strip() or parts[1] != parts[1].strip():
                        raise ValueError('expected stop:event_id or reduce_to:event_id:new_amount')
                    if parts[0] == 'stop' and len(parts) == 2:
                        pass
                    elif parts[0] == 'reduce_to' and len(parts) == 3:
                        if _decimal(parts[2]) < 0:
                            raise ValueError('reduced amount must be nonnegative')
                    else:
                        raise ValueError('unrecognized spending change')
                    if parts[1] in seen:
                        raise ValueError('an event may appear in only one spending change')
                    seen.add(parts[1])
        except ValueError as exc:
            changes.append(f'Row {i}: invalid spending_changes_needed: {exc}')
        status, method = row['affordability_status'], row['recommended_payment_method']
        if status not in {'affordable_now', 'affordable_with_plan', 'affordable_later', 'not_affordable'}:
            enums.append(f'Row {i}: invalid affordability_status')
        if method not in {'full_payment', 'partial_payment', 'installments', 'wait', 'not_recommended'}:
            enums.append(f'Row {i}: invalid recommended_payment_method')
        src = source.get(row['request_id'])
        safe = requested = request_date = earliest = None
        try:
            safe = _decimal(row['amount_safe_to_pay'])
            if safe < 0:
                raise ValueError('amount_safe_to_pay is negative')
            if src is not None:
                requested = _decimal(src['requested_amount'])
                if requested < 0 or safe > requested:
                    raise ValueError('amount_safe_to_pay exceeds requested_amount or requested amount is negative')
        except ValueError as exc:
            amounts.append(f'Row {i}: {exc}')
        try:
            if src is not None:
                request_date = _date(src['request_date'])
            if row['earliest_date_for_full_payment']:
                earliest = _date(row['earliest_date_for_full_payment'])
            if status == 'affordable_now' and (earliest is None or earliest != request_date):
                raise ValueError('affordable_now requires earliest date equal to request_date')
        except ValueError as exc:
            dates.append(f'Row {i}: {exc}')
        payments = []
        try:
            if row['payment_plan'] != 'none':
                for item in row['payment_plan'].split('|'):
                    day, amount = item.split(':')
                    day, amount = _date(day), _decimal(amount)
                    if amount <= 0:
                        raise ValueError('plan payment must be positive')
                    if payments and day < payments[-1][0]:
                        raise ValueError('plan dates must be chronological')
                    payments.append((day, amount))
            if method == 'partial_payment':
                if src is None or safe is None or requested is None or not (0 < safe < requested) or status != 'affordable_with_plan':
                    raise ValueError('partial_payment requires affordable_with_plan and 0 < safe < requested')
                if len(payments) != 2 or payments != [(request_date, safe), (earliest, _remainder(requested, safe))]:
                    raise ValueError('partial_payment requires safe on request_date and remainder on earliest date')
                if not src.get('desired_completion_date'):
                    raise ValueError('partial_payment requires input desired_completion_date')
                if earliest is None or earliest > _date(src['desired_completion_date']):
                    raise ValueError('partial_payment completion exceeds desired completion date')
        except (ValueError, DecimalException) as exc:
            plans.append(f'Row {i}: invalid payment plan: {exc}')
    return [_check('September unique input ID coverage', errors), _check('September categorical fields', enums),
            _check('September finite bounded payment amount', amounts), _check('September dates', dates),
            _check('September payment plan structure', plans),
            _check('September spending change syntax', changes),
            _check('September nonempty explanation', explanations),
            result('September financial and consent semantics', 'unknown', ['Input consent, installment eligibility, 90-day horizons, affordability calculations, and explanation quality are not implemented; require the full input schema and independent review'])]


def evaluate_historical(output_path, task):
    """Return evidence checks; malformed files fail closed, unsupported tasks raise.

    Relative input_csv and output paths resolve against the current working directory."""
    plugin = task.get('plugin')
    if plugin not in {'may26_schema', 'june26_schema', 'september26_schema'}:
        raise ValueError('Unsupported historical schema plugin')
    if not task.get('input_csv'):
        raise ValueError('Historical task requires input_csv')
    try:
        input_headers, inputs = _read(task['input_csv'])
        output_headers, outputs = _read(output_path)
    except (OSError, ValueError, csv.Error, UnicodeError) as exc:
        return [result('Historical CSV readability', 'fail', [str(exc)])]
    if plugin == 'may26_schema':
        try:
            input_headers, inputs = _may_headers(input_headers, inputs)
            output_headers, outputs = _may_headers(output_headers, outputs)
        except ValueError as exc:
            return [result('May unambiguous header names', 'fail', [str(exc)])]
        if not {'issue', 'subject', 'company'} <= set(input_headers):
            return [result('May required input columns', 'fail', ['Required: issue, subject, company (title-case aliases accepted)'])]
        if not set(MAY_REQUIRED) <= set(output_headers):
            return [result('May required output columns', 'fail', ['Required: ' + ','.join(MAY_REQUIRED) + '; additional columns and column reordering are allowed'])]
        checks = [result('May required output columns', 'pass', ['Required fields present; no unsupported fixed column order or product-area enum imposed'])]
        return checks + _may(inputs, outputs, {'issue', 'subject', 'company'} <= set(output_headers))
    expected = JUNE_HEADERS if plugin == 'june26_schema' else SEPTEMBER_HEADERS
    if output_headers != expected:
        return [result('Historical ordered output headers', 'fail', ['Required ordered headers: ' + ','.join(expected)])]
    required = JUNE_HEADERS[:4] if plugin == 'june26_schema' else ['request_id', 'requested_amount', 'request_date']
    if not set(required) <= set(input_headers):
        return [result('Historical required input headers', 'fail', ['Required input columns: ' + ','.join(required)])]
    checks = [result('Historical ordered output headers', 'pass', ['Exact ordered output schema'])]
    return checks + (_june(inputs, outputs) if plugin == 'june26_schema' else _september(inputs, outputs))
