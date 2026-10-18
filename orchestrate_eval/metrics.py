"""Exact string metrics for an explicitly supplied local labelled CSV.

References are user-supplied labels, never asserted to be official gold answers.
ID alignment is independent of row order; missing answers count as mismatches.
"""
from collections import Counter
import csv

from .checks import result
from .fileio import digest_file
from .historical import _read

CASE_DETAIL_LIMIT = 1000
CONFUSION_DETAIL_LIMIT = 200


def evaluate_labelled(output_path, task):
    reference = task.get("reference_csv")
    key = task.get("id_column")
    fields = task.get("fields")
    if not isinstance(reference, str) or not reference or not isinstance(key, str) or not key:
        raise ValueError("labelled_csv requires reference_csv and id_column strings")
    if not isinstance(fields, list) or not fields or not all(isinstance(f, str) and f for f in fields):
        raise ValueError("labelled_csv requires a nonempty fields list")
    if len(set(fields)) != len(fields) or key in fields:
        raise ValueError("Metric fields must be unique and exclude the ID column")
    if len(fields) > 128 or any(len(field) > 128 for field in [key] + fields):
        raise ValueError("Local metric limit: 128 fields, with column names at most 128 characters")
    headers, expected_rows = _read(reference)
    if not expected_rows or not {key, *fields} <= set(headers):
        raise ValueError("Reference needs labelled rows and every configured field/ID column")
    expected = {row[key]: row for row in expected_rows}
    if len(expected) != len(expected_rows) or any(not identifier.strip() for identifier in expected):
        raise ValueError("Reference IDs must be nonempty and unique")
    reference_hash = digest_file(reference)
    try:
        candidate_headers, rows = _read(output_path)
    except (ValueError, OSError, UnicodeError, csv.Error) as exc:
        return [result("Labelled CSV readability", "fail", [str(exc)])], None
    if not {key, *fields} <= set(candidate_headers):
        return [result("Labelled CSV required columns", "fail", ["Required: " + ", ".join([key] + fields)])], None
    ids = [row[key] for row in rows]
    if len(ids) != len(set(ids)) or any(not identifier.strip() for identifier in ids):
        return [result("Labelled CSV unique IDs", "fail", ["Candidate IDs must be nonempty and unique; ambiguous rows are not scored"])], None
    candidate = {row[key]: row for row in rows}
    missing = sorted(set(expected) - set(candidate))
    extra = sorted(set(candidate) - set(expected))
    checks = [result("Labelled CSV ID coverage", "fail" if missing or extra else "pass",
                     [f"Missing IDs: {missing[:50]}", f"Unexpected IDs: {extra[:50]}"])]
    per_field = {}
    per_case = []
    total_matches = 0
    for name in fields:
        correct = 0
        confusion = Counter()
        for identifier, row in expected.items():
            predicted = candidate[identifier][name] if identifier in candidate else None
            correct += predicted == row[name]
            confusion[(row[name], predicted)] += 1
        per_field[name] = {"matches": correct, "labels": len(expected), "accuracy": correct / len(expected),
                           "confusion_entry_count": len(confusion), "confusion_truncated": len(confusion) > CONFUSION_DETAIL_LIMIT,
                           "confusion": [{"expected": gold, "predicted": prediction, "count": count}
                                         for (gold, prediction), count in sorted(confusion.items(), key=lambda item: (item[0][0], str(item[0][1])))[:CONFUSION_DETAIL_LIMIT]]}
        total_matches += correct
        checks.append(result("Labelled exact field: " + name, "pass" if correct == len(expected) else "fail",
                             [f"{correct}/{len(expected)} exact string matches against the supplied local reference; missing IDs count as mismatches"]))
    for identifier, row in expected.items():
        mismatches = [name for name in fields if identifier not in candidate or candidate[identifier][name] != row[name]]
        per_case.append({"id": identifier, "present": identifier in candidate, "exact_match": not mismatches,
                         "mismatched_fields": mismatches})
    metrics = {"method": "exact_string_local_labels", "reference_sha256": reference_hash,
               "reference_description": task.get("reference_description", "User-supplied local labels; provenance unverified"),
               "rows": len(expected), "fields": per_field,
               "micro_accuracy": total_matches / (len(expected) * len(fields)),
               "exact_row_accuracy": sum(case["exact_match"] for case in per_case) / len(expected),
               "missing_ids": missing, "unexpected_ids": extra,
               "per_case": sorted(per_case, key=lambda case: case['exact_match'])[:CASE_DETAIL_LIMIT],
               "case_details_truncated": len(per_case) > CASE_DETAIL_LIMIT,
               "detail_policy": "Aggregates cover every reference row. At most 1,000 case details (mismatches first, reference order within each group) and 200 sorted confusion entries per field are embedded; truncation flags/counts disclose omitted details.",
               "limitations": "Local exact string comparisons only. No semantic equivalence, numeric tolerance, official score, or proof of label correctness. Unexpected IDs fail coverage but do not change the expected-label accuracy denominator."}
    return checks, metrics


def compare_reports(reports):
    """Compare only metrics tied to the same exact task and reference snapshots."""
    if len(reports) < 2:
        raise ValueError("Compare requires at least two evaluation reports")
    if not all(isinstance(report, dict) for report in reports):
        raise ValueError("Every comparison input must be an evaluation report object")
    if not all(isinstance(report.get('metrics'), dict) for report in reports):
        raise ValueError("Every comparison input needs labelled metric data")
    task_hash = reports[0].get("task_sha256")
    reference_hash = (reports[0].get("metrics") or {}).get("reference_sha256")
    if not task_hash or not reference_hash:
        raise ValueError("Compare requires labelled_csv reports with task/reference hashes")
    rows = []
    for index, report in enumerate(reports, 1):
        metrics = report.get("metrics")
        if not isinstance(metrics, dict) or report.get("task_sha256") != task_hash or metrics.get("reference_sha256") != reference_hash:
            raise ValueError("Refusing to compare different task/reference hashes or missing metrics")
        if metrics.get("method") != "exact_string_local_labels":
            raise ValueError("Unsupported metric method")
        if not isinstance(metrics.get('fields'), dict) or not all(isinstance(value, dict) for value in metrics['fields'].values()):
            raise ValueError('Malformed per-field metrics')
        rows.append({"label": report.get("label") or f"configuration-{index}", "status": report.get("status"),
                     "output_sha256": report.get("output_sha256"), "micro_accuracy": metrics["micro_accuracy"],
                     "exact_row_accuracy": metrics["exact_row_accuracy"],
                     "per_field_accuracy": {name: values["accuracy"] for name, values in metrics["fields"].items()},
                     "missing_ids": len(metrics["missing_ids"]), "unexpected_ids": len(metrics["unexpected_ids"])})
    return {"schema_version": 1, "task_sha256": task_hash, "reference_sha256": reference_hash,
            "configurations": rows, "official_score": None,
            "limitations": "Local reference accuracy only; no official points. Label provenance and report claims are unverified. Same hashes do not establish equal runtime settings, cost, or fresh-model execution."}
