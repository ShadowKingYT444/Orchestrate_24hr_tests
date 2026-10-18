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
    bench = subs.add_parser('benchmark',help='Execute trusted agents, judge semantic/code/transcript quality, and compare local scores')
    actions=bench.add_subparsers(dest='benchmark_action',required=True)
    br=actions.add_parser('run')
    br.add_argument('--command-json',required=True);br.add_argument('--cwd',required=True);br.add_argument('--allow-exec',action='store_true')
    br.add_argument('--seed',type=int,default=0);br.add_argument('--split',choices=['dev','holdout','all'],default='holdout')
    br.add_argument('--repeats',type=int,default=1);br.add_argument('--timeout',type=float,default=5);br.add_argument('--report-dir',default='reports/benchmark')
    br.add_argument('--source');br.add_argument('--transcript');br.add_argument('--judge-config');br.add_argument('--allow-judge-network',action='store_true')
    br.add_argument('--casepack',help='Your own versioned documents/cases/references JSON; gold is not sent to the agent')
    be=actions.add_parser('judge-export');be.add_argument('--source',required=True);be.add_argument('--transcript');be.add_argument('--benchmark-report');be.add_argument('--output',required=True)
    bi=actions.add_parser('judge-import');bi.add_argument('--bundle',required=True);bi.add_argument('--review',required=True);bi.add_argument('--benchmark-report');bi.add_argument('--report-dir',default='reports/judged')
    bj=actions.add_parser('judge');bj.add_argument('--bundle',required=True);bj.add_argument('--output',required=True)
    bj.add_argument('--endpoint');bj.add_argument('--model');bj.add_argument('--api-key-env',default='OPENAI_API_KEY');bj.add_argument('--allow-judge-network',action='store_true')
    bj.add_argument('--command-json');bj.add_argument('--cwd',default='.');bj.add_argument('--allow-judge-exec',action='store_true')
    bj.add_argument('--max-cost-usd',type=float,required=True);bj.add_argument('--input-price-per-million',type=float);bj.add_argument('--output-price-per-million',type=float);bj.add_argument('--max-output-tokens',type=int,default=6000);bj.add_argument('--repeats',type=int,default=1)
    bc=actions.add_parser('compare');bc.add_argument('reports',nargs='+');bc.add_argument('--report-dir',default='reports/benchmark-comparison')
    bt=actions.add_parser('cases');bt.add_argument('--output',required=True);bt.add_argument('--seed',type=int,default=0);bt.add_argument('--split',choices=['dev','holdout','all'],default='all')
    args = parser.parse_args(argv)
    try:
        if args.action=='benchmark':
            from .benchmark import run_benchmark,compare_benchmarks,write_benchmark_report,apply_semantics
            from .judging import export_bundle,import_review,judge_http,aggregate_reviews
            if args.benchmark_action=='cases':
                from .benchmark_cases import casepack
                Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(casepack(args.seed,args.split),indent=2)+'\n')
                print(json.dumps({'casepack_template':args.output,'warning':'Contains reference answers; keep this host-side, never give it to the agent'}));return 0
            if args.benchmark_action=='run':
                report=run_benchmark(strict_json(args.command_json),args.cwd,args.report_dir,args.seed,args.split,args.repeats,args.timeout,args.allow_exec,args.casepack)
                if args.judge_config:
                    if not args.source:raise ValueError('Automatic judging requires --source and optional genuine --transcript')
                    config=read_json(args.judge_config)
                    bundle=export_bundle(args.source,Path(args.report_dir)/'judge-bundle.json',args.transcript,Path(args.report_dir)/'benchmark.json')
                    accepted=judge_http(bundle,config['endpoint'],config['model'],config.get('api_key_env','OPENAI_API_KEY'),config['max_cost_usd'],config['input_price_per_million'],config['output_price_per_million'],config.get('max_output_tokens',6000),args.allow_judge_network,Path(args.report_dir)/'judge-raw-response.json')
                    (Path(args.report_dir)/'accepted-review.json').write_text(json.dumps(accepted,indent=2)+'\n')
                    report=apply_semantics(report,accepted);write_benchmark_report(report,args.report_dir)
                print(json.dumps({'report':str(Path(args.report_dir)/'benchmark.html'),'machine_component_mean_85':report['machine_component_mean_85'],'output_score_100':report['output_score_100'],'semantic_judge_pending':report['output_score_100'] is None}))
                return 0
            if args.benchmark_action=='judge-export':
                bundle=export_bundle(args.source,args.output,args.transcript,args.benchmark_report)
                print(json.dumps({'bundle':args.output,'bundle_id':bundle['bundle_id'],'transcript_available':bundle['transcript_available']}));return 0
            if args.benchmark_action=='judge-import':
                bundle=read_json(args.bundle);accepted=import_review(bundle,read_json(args.review))
                destination=Path(args.report_dir);destination.mkdir(parents=True,exist_ok=True)
                (destination/'accepted-review.json').write_text(json.dumps(accepted,indent=2)+'\n')
                if args.benchmark_report:
                    report=apply_semantics(read_json(args.benchmark_report),accepted);write_benchmark_report(report,destination)
                    print(json.dumps(report['scorecard']))
                else:print(json.dumps({'category_scores':accepted['category_scores'],'estimate_only':True}))
                return 0
            if args.benchmark_action=='judge':
                import math
                if not math.isfinite(args.max_cost_usd) or args.max_cost_usd<0:raise ValueError('Judge budget must be finite and nonnegative before execution')
                bundle=read_json(args.bundle)
                if args.command_json:
                    if args.allow_judge_network:raise ValueError('Choose one explicit judge adapter')
                    if args.repeats!=1:raise ValueError('Local worker repeats are explicitly orchestrated by the worker; CLI --repeats is for the HTTP adapter')
                    result=run_command(strict_json(args.command_json),args.cwd,120,args.allow_judge_exec,stdin_text=json.dumps({'bundle':bundle,'budget':{'max_cost_usd':args.max_cost_usd,'external_calls_allowed':args.max_cost_usd>0}})+'\n')
                    if result['status']!='pass':raise ValueError('Local judge worker failed; no review accepted')
                    review=strict_json(result['stdout']);accepted=import_review(bundle,review)
                    cost=review.get('usage',{}).get('cost_usd')
                    if cost is not None and (not isinstance(cost,(int,float)) or isinstance(cost,bool) or not math.isfinite(cost) or cost<0 or cost>args.max_cost_usd):raise ValueError('Worker-reported cost exceeds declared budget or is invalid')
                    accepted['budget']={'max_cost_usd':args.max_cost_usd,'worker_reported_cost_usd':cost,'enforcement':'Cooperative trusted worker only; not an OS/network/payment hard cap'}
                else:
                    if not args.endpoint or not args.model or args.input_price_per_million is None or args.output_price_per_million is None:raise ValueError('HTTP judge requires endpoint/model and explicit current input/output prices')
                    if not 1<=args.repeats<=5:raise ValueError('Judge repeats must be1..5')
                    opinions=[judge_http(bundle,args.endpoint,args.model,args.api_key_env,args.max_cost_usd/args.repeats,args.input_price_per_million,args.output_price_per_million,args.max_output_tokens,args.allow_judge_network,args.output+'.raw-'+str(index)+'.json') for index in range(args.repeats)]
                    accepted=opinions[0] if len(opinions)==1 else aggregate_reviews(bundle,opinions)
                Path(args.output).parent.mkdir(parents=True,exist_ok=True);Path(args.output).write_text(json.dumps(accepted['review'],indent=2)+'\n');Path(args.output+'.metadata.json').write_text(json.dumps(accepted,indent=2)+'\n')
                print(json.dumps({'review':args.output,'category_scores':accepted['category_scores']}));return 0
            result=compare_benchmarks([read_json(path) for path in args.reports]);destination=Path(args.report_dir);destination.mkdir(parents=True,exist_ok=True)
            (destination/'comparison.json').write_text(json.dumps(result,indent=2)+'\n')
            import html
            (destination/'comparison.html').write_text('<!doctype html><html><meta charset="utf-8"><h1>Local agent score comparison</h1><pre>'+html.escape(json.dumps(result,indent=2))+'</pre></html>')
            print(json.dumps({'comparison':str(destination/'comparison.html')}));return 0
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
