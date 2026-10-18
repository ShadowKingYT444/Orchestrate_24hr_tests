"""Non-executing source checks and a synthetic exact-match plugin."""
import ast
import json
import math
from itertools import islice
from pathlib import Path
from .fileio import MAX_FILE, read_bounded, digest_file


def strict_json(text):
    def pairs(items):
        output = {}
        for key, value in items:
            if key in output:
                raise ValueError(f"Duplicate JSON key: {key}")
            output[key] = value
        return output
    def reject_constant(value):
        raise ValueError(f"Nonfinite JSON constant: {value}")
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError(f"Nonfinite JSON number: {value}")
        return number
    try:
        data = json.loads(text, object_pairs_hook=pairs, parse_constant=reject_constant, parse_float=finite_float)
    except RecursionError:
        raise ValueError("JSON nesting is too deep") from None
    stack = [(data, 0)]
    while stack:
        value, depth = stack.pop()
        if depth > 128:
            raise ValueError("JSON nesting exceeds the local 128-level limit")
        if isinstance(value, dict):
            stack.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value)
    return data

def read_json(path):
    return strict_json(read_bounded(path).decode("utf-8"))

def result(name, status, evidence, kind="objective"):
    return {"name": name, "status": status, "kind": kind, "evidence": evidence}

def source_checks(root):
    root = Path(root)
    if not root.is_dir() or root.is_symlink():
        raise ValueError("Source must be a real directory")
    checks = []
    for label, names in [("setup instructions", ["README.md"]),
                         ("dependency declaration", ["pyproject.toml", "requirements.txt", "package.json"]),
                         ("tests present", ["tests"]),
                         ("dependency lock present", ["requirements.lock", "uv.lock", "poetry.lock", "package-lock.json"])]:
        found = [n for n in names if (root / n).exists() and not (root / n).is_symlink()]
        checks.append(result(label, "pass" if found else "fail", found or ["Not found"], "proxy"))
    files = sorted(islice(root.rglob("*.py"), 2001))
    errors = []
    for path in files[:2000]:
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root.parent):
            errors.append(f"{path.relative_to(root)}: symlink refused")
            continue
        try:
            ast.parse(read_bounded(path).decode("utf-8"), filename=str(path.relative_to(root)))
        except (SyntaxError, UnicodeError, ValueError, OSError) as exc:
            errors.append(f"{path.relative_to(root)}: {type(exc).__name__}")
    if len(files) > 2000:
        errors.append("Source file limit exceeded")
    checks.append(result("Python syntax (not correctness)", "fail" if errors else ("pass" if files else "unknown"), errors or [f"Parsed {len(files)} Python files; no candidate code executed"]))
    return checks

def synthetic_exact(candidate, task):
    """Only synthetic fixtures: IDs and JSON values must match exactly."""
    expected = task.get("expected")
    if not isinstance(expected, dict) or not expected:
        raise ValueError("Synthetic task needs a non-empty expected object")
    if not isinstance(candidate, dict) or not isinstance(candidate.get("answers"), dict):
        return [result("synthetic exact match", "fail", ["Missing answers object"])]
    answers = candidate["answers"]
    def same(a, b):
        return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)
    checks = [result(f"synthetic case {key}", "pass" if key in answers and same(answers[key], value) else "fail", [f"Exact JSON equality for case {key}"]) for key, value in expected.items()]
    checks.append(result("no unexpected answer IDs", "pass" if set(answers) <= set(expected) else "fail", ["Expected IDs: " + ", ".join(expected)]))
    return checks

BUILTIN_PLUGINS = {"synthetic_exact": synthetic_exact}

def transcript_checks(path):
    if path is None:
        return [result("transcript provenance", "unknown", ["No transcript supplied"]) ]
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("Transcript must be an object")
    events = data.get("events", [])
    valid = isinstance(events, list) and bool(events) and all(isinstance(e, dict) and e.get("role") in {"user", "assistant", "tool"} and isinstance(e.get("content"), str) and isinstance(e.get("timestamp"), str) and e["timestamp"].strip() for e in events)
    provenance = data.get("provenance", {})
    declared = isinstance(provenance, dict) and all(isinstance(provenance.get(k), str) and provenance[k].strip() for k in ("source", "exported_at", "run_id"))
    digest = digest_file(path)
    return [result("transcript schema", "pass" if valid else "fail", ["Requires timestamped role/content events"]),
            result("declared provenance", "pass" if declared else "fail", ["Self-reported source/exported_at/run_id; not proof of authenticity"], "proxy"),
            result("transcript authenticity", "unknown", [f"SHA-256 {digest}; digest binds this file only, cannot prove events occurred"]),
            result("transcript quality", "unknown", ["Human review required: useful planning, tool rationale, verification, corrections; no credit for length"], "subjective")]
