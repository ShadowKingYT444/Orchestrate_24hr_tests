import argparse
import json
from pathlib import Path
from .checks import BUILTIN_PLUGINS, read_json, result, source_checks, transcript_checks, strict_json
from .report import write_report
from .runner import run_command
from .review import validate_review
from .fileio import digest_file, read_bounded

def evaluate(args):
    task = read_json(args.task)
    if not isinstance(task, dict):
        raise ValueError("Task config must be an object")
    if "profile" in task and not isinstance(task["profile"], str):
        raise ValueError("Task profile must be a string")
    plugin = task.get("plugin")
    output = []
    metrics = None
    if plugin == "labelled_csv":
        from .metrics import evaluate_labelled
        output, metrics = evaluate_labelled(args.output, task)
    elif plugin in {"may26_schema", "june26_schema", "september26_schema"}:
        from .historical import evaluate_historical
        output = evaluate_historical(args.output, task)
    elif plugin not in BUILTIN_PLUGINS:
        output = [result("task-specific evaluator", "unknown", ["Missing/unsupported plugin; no output score can be established"])]
    else:
        output = BUILTIN_PLUGINS[plugin](read_json(args.output), task)
    try:
        output_hash = digest_file(args.output)
    except (ValueError, OSError) as exc:
        output_hash = None
        output.append(result("Bounded regular output file", "fail", [str(exc)]))
    checks = {"code": source_checks(args.source) if args.source else [result("source review", "unknown", ["No source directory supplied"])],
              "output": output, "coding_transcript": transcript_checks(args.transcript)}
    checks["code"].append(result("code quality rubric", "unknown", ["Human review needed: architecture, implemented behavior, robustness and reproducible experiments; presence checks do not establish quality"], "subjective"))
    if args.review:
        checks["advisory_review"] = validate_review(read_json(args.review))
    if args.judge_command_json:
        if not args.source:
            raise ValueError("Judge command requires --source as its working directory")
        judge = run_command(json.loads(args.judge_command_json), args.source, args.timeout, args.allow_exec)
        if judge["status"] != "pass":
            checks["advisory_review"] = [result("configured judge", "unknown", ["Judge failed; no review accepted"], "subjective")]
        else:
            review = strict_json(judge["stdout"])
            if not isinstance(review, dict) or review.get("origin") != "configured_judge":
                raise ValueError("Judge output must declare origin=configured_judge")
            checks["advisory_review"] = validate_review(review)
    if args.archive:
        from .archive import inspect_submission_archive
        inspection = inspect_submission_archive(Path(args.archive))
        checks["packaging"] = [result("ZIP safety and size", inspection["status"], inspection["issues"] or [json.dumps(inspection)])]
    statuses = [c["status"] for group in checks.values() for c in group if c["kind"] == "objective"]
    status = "fail" if "fail" in statuses else "incomplete" if "unknown" in statuses else "pass"
    scorecards = {category: {kind: {state: sum(c["kind"] == kind and c["status"] == state for c in group)
                                  for state in ("pass", "fail", "unknown")}
                            for kind in ("objective", "proxy", "subjective")}
                  for category, group in checks.items()}
    report = {"schema_version": 1, "status": status, "profile": task.get("profile", "custom"),
              "label": args.label, "task_sha256": digest_file(args.task),
              "output_sha256": output_hash, "metrics": metrics, "scorecards": scorecards,
              "official_score": None, "checks": checks,
              "coverage": {"published_generic_weights": {"code": 30, "output": 30, "coding_transcript": 10, "voice_interview": 30},
                           "voice_interview": "excluded by design", "maximum_in_scope_weight": 70,
                           "earned_points": None, "renormalized": False,
                           "output_evaluator": plugin, "subjective_categories": "Unscored: require evidence-based review",
                           "edition_override": "Confirm actual challenge rules; historical profiles are not October scoring",
                           "transcript": "Coding-tool conversation export, not runtime agent logs"}}
    write_report(report, args.report_dir)
    print(json.dumps({"status": status, "report": str(Path(args.report_dir) / "report.html"), "official_score": None}))
    return 1 if status == "fail" else 2 if status == "incomplete" else 0

def main(argv=None):
    parser = argparse.ArgumentParser(description="Offline diagnostics, not an official Orchestrate scorer")
    subs = parser.add_subparsers(dest="action", required=True)
    ev = subs.add_parser("evaluate")
    for arg in ("task", "output"):
        ev.add_argument("--" + arg, required=True)
    for arg in ("source", "transcript", "archive", "review", "judge-command-json"):
        ev.add_argument("--" + arg)
    ev.add_argument("--report-dir", default="reports/latest")
    ev.add_argument("--label", help="Configuration name recorded in this report")
    ev.add_argument("--allow-exec", action="store_true")
    ev.add_argument("--timeout", type=float, default=60)
    run = subs.add_parser("run", help="Explicit opt-in trusted subprocess; NOT a sandbox")
    run.add_argument("--command-json", required=True)
    run.add_argument("--cwd", required=True)
    run.add_argument("--timeout", type=float, default=60)
    run.add_argument("--allow-exec", action="store_true")
    run.add_argument("--report-dir", default="reports/run")
    archive = subs.add_parser("archive")
    archive.add_argument("path")
    compare = subs.add_parser("compare", help="Compare local labelled-CSV reports using identical task/reference hashes")
    compare.add_argument("reports", nargs="+")
    compare.add_argument("--report-dir", default="reports/comparison")
    public = subs.add_parser("validate-public", help="Offline calibration against pinned public May-winner artifacts; never executes the agent")
    public.add_argument("--candidate-dir", required=True)
    public.add_argument("--official-dir", required=True)
    public.add_argument("--report-dir", default="reports/public-validation")
    args = parser.parse_args(argv)
    try:
        if args.action == "evaluate":
            return evaluate(args)
        if args.action == "validate-public":
            from .public_validation import validate_public
            report = validate_public(args.candidate_dir, args.official_dir, args.report_dir)
            print(json.dumps({'status': report['calibration_status'], 'report': str(Path(args.report_dir) / 'validation.json'), 'official_score': None}))
            return 0 if report['calibration_status'] == 'pass' else 1
        if args.action == "compare":
            from .metrics import compare_reports
            from .report import write_comparison
            report = compare_reports([strict_json(read_bounded(path, 50_000_000).decode('utf-8')) for path in args.reports])
            write_comparison(report, args.report_dir)
            print(json.dumps({"comparison": str(Path(args.report_dir) / "comparison.html"), "official_score": None}))
            return 0
        if args.action == "archive":
            from .archive import inspect_submission_archive
            report = inspect_submission_archive(Path(args.path))
            print(json.dumps(report, indent=2))
            return 0 if report["status"] == "pass" else 1
        report = run_command(json.loads(args.command_json), args.cwd, args.timeout, args.allow_exec)
        destination = Path(args.report_dir); destination.mkdir(parents=True, exist_ok=True)
        (destination / "run.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({k: v for k, v in report.items() if k not in ("stdout", "stderr")}))
        return 0 if report["status"] == "pass" else 1
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(f"Evaluation error: {exc}")
        return 2
