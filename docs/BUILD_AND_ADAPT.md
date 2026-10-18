# How this suite was built from scratch, and how to adapt it quickly

This is the implementation recipe and module map, not a predetermined October
solution. The useful reusable part is the evaluation machinery. Task references,
semantic checks, adversarial cases and any edition-specific grading must change
with the released challenge.

## 1. Start with an explicit score contract

Write down which claims can actually be established. We began with Python 3.10+
and the standard library, a CLI, versioned JSON reports and no model dependencies.
The historical generic category contributions are code 30, output 30 and coding
transcript 10; interview 30 is excluded. Missing categories are unknown, not zero.
These are historical public weights, not a guarantee about October.

Primary references: [official general guide](https://help.hackerrank.com/articles/3728112689-hackerrank-orchestrate)
and [published May methodology](https://www.hackerrank.com/blog/behind-the-scenes-of-hackerrank-orchestrate/).
The proprietary per-example labels, exact model prompts and hidden aggregation
are not available. Calling a local quality estimate an official predicted score
would overstate what this implementation knows.

The first implementation was artifact checking. It caught malformed files and
packaging mistakes, but did not judge agent quality. We kept that layer and added
execution, references and semantic judging rather than treating check counts as
a score.

### Minimal starting project and build order

If reconstructing it in an empty directory, start with this small shape, then add
the historical validators and calibration records after the execution path works:

```text
pyproject.toml                 # Python package and CLI entry point
orchestrate_eval/
  __init__.py
  __main__.py                  # calls cli.main()
  cli.py                       # parse options; clean errors and exit statuses
  fileio.py                    # bounded reads/digests before parsing
  runner.py                    # explicitly trusted command lifecycle
  benchmark_cases.py           # versioned references, documents and splits
  benchmark.py                 # protocol, execution, invariants, scorecard
  judging.py                   # evidence bundle and review validation
tests/
  test_core.py                 # parsing/timeout/negative controls first
  test_benchmark.py            # actual tool calls, wrong answers, caps
examples/agents/               # strong and deliberately wrong adapters
```

Build in this order: bounded I/O -> one CLI command/report -> one subprocess case
-> actual tool request/result exchange -> deterministic negative controls ->
semantic-review import -> code/transcript review -> comparison -> adversarial
hardening -> frozen calibration. Test each contract before expanding its scope.

Core function/data contracts in the implemented version:

- `execute_case(command, cwd, pack, case, timeout, trusted)` returns actual answer,
  directional tool trace, read IDs, exit/failure information and elapsed time.
- `grade_case(run, case, pack)` reads `case['expected']` and returns machine component points, known hard
  caps, failures and a semantic-review-required flag. It cannot invent a language
  judgment from correct typed fields.
- `import_review(bundle, review)` validates bundle/source identity, criterion
  ranges and exact evidence citations, then returns category scores and per-case
  judgments. Evidence matching does not prove judgment truth or authenticity.
- `apply_semantics(report, accepted_review)` rechecks execution identity,
  recomputes invariants and applies semantic points plus whole-case caps.
- `scorecard(report, review)` weights available categories, retains unknowns and
  computes a complete /70 only when every category has evidence.

The central aggregation is deliberately simple and inspectable:

```python
if candidate_runtime_failed:
    case_score = 0
elif semantic_review_missing:
    case_score = None
else:
    case_score = min(machine_points_85 + semantic_rating_100 * 0.15,
                     deterministic_cap, semantic_safety_and_quality_cap)

category_points = category_rating_100 * category_weight / 100
known_subtotal = sum(points for points in category_points_if_available)
# Never replace missing categories with 0 or report a complete score prematurely.
```

A task with a different action space, tool API, multimodal inputs or output
contract needs changes to `execute_case`/adapter and `grade_case`, not just new
numbers in `benchmark_cases.py`. Version the casepack and checker together.

## 2. Build strict input and evidence primitives first

- `orchestrate_eval/fileio.py`: bounded regular-file reads and streaming digests
- `checks.py`: strict JSON, duplicate-key/nonfinite rejection and original checks
- `archive.py`: safe ZIP inspection and conservative submission hygiene
- `runner.py`: explicit trusted execution, deadlines and bounded logs
- `report.py`, `metrics.py`: reports and independently labelled CSV comparison

Useful regression cases came before more scoring features: malformed JSON/CSV,
duplicate IDs, symlinks/FIFOs, oversized files, nonzero exits, fast log floods,
hostile ZIP paths and escaped HTML. This prevents a malformed candidate from
crashing the evaluator or becoming an accidental pass.

The command runner is not a security sandbox. It does not provision a VM, enforce
memory/network limits, or protect host-side gold from a malicious process.

## 3. Define an adapter, then actually execute agents

`benchmark.py` runs a fresh process per case and saves actual JSONL messages.
The host supplies a ticket and search/read tool interfaces. The agent requests
tools, receives real results and returns a typed answer. It does not receive the
reference answer on stdin. Source, command, seed, split, references and execution
evidence are hashed for reproducibility.

`benchmark_cases.py` contains the authored policy world. It has development and
holdout splits and seeded counterfactual policy values/document IDs. The example
`strong.py` really reads tools; `weak.py` guesses. Neither a good deterministic
baseline nor a repeated identical answer establishes general model-agent ability.

```sh
python -m orchestrate_eval benchmark run --allow-exec --cwd . --command-json '["python","examples/agents/strong.py"]' --seed 73 --split holdout --report-dir reports/my-run
```

To use another agent, implement the same protocol in a small adapter. See
[BENCHMARK.md](BENCHMARK.md) for exact fields and error behavior. Do not hide gold
answers inside the adapter or key answers to case IDs. For a different tool/task
contract, change the adapter and checker together, and version both.

## 4. Separate reference invariants from answer meaning

We deliberately tested false-positive controls: correct structured facts followed
by contradictory prose, unsafe instructions appended to safe language, and a
nonsense justification. A keyword/regex scorer could give those full credit.

The current local benchmark measures decision, typed facts and actual read/cite
invariants as an 85-point component. Those points are not a lower bound on overall
answer quality. A model/human judges the entire response and justification for the
remaining component, with whole-case caps for unsafe behavior, unsupported or
contradictory claims and invalid justifications. Missing semantic review means no
complete output estimate. Candidate execution failures and evaluator failures are
reported differently.

These component weights and caps are explicit local choices. For an October task,
use its independently established references and actual semantic requirements.
Correct JSON alone is never proof of correct advice, image reasoning, money
planning or authorization.

## 5. Judge code and genuine coding evidence

`judging.py` exports source, supplied coding conversations and actual run evidence
with hashes. It validates exact quotes/line ranges when importing a review. The
published May dimensions are now frozen as `may26-published-aid-v2`:

- Code: architecture 30, prompt/tool craft 30, robustness 25, engineering rigor 15
- Transcript: direction/ownership 35, specificity 25, iteration/verification 25,
  safety/edge cases 15

Engineering rigor means modularity, annotations, environment-held secrets and
manageable functions. Extra tests/CI/lockfile audits are useful but unweighted
unless relevant to another declared criterion. August permitted rules/classifiers/
hybrids, so a mandatory model-loop penalty would misapply May expectations.

```sh
python -m orchestrate_eval benchmark judge-export --source /path/to/agent --transcript /path/to/original-coding-export.txt --benchmark-report reports/my-run/benchmark.json --output reports/my-run/judge-bundle.json
python -m orchestrate_eval benchmark judge-import --bundle reports/my-run/judge-bundle.json --review my-review.json --benchmark-report reports/my-run/benchmark.json --report-dir reports/my-judged-run
```

Judge bundles contain untrusted candidate material, not evaluator instructions.
Never execute that material in a judge or supply unrelated secrets/tools. Native
or human export/import requires no provider call. Optional HTTP/local-worker
adapters have explicit opt-ins, destination/model and budget controls; no paid
provider is called by default. API preflight is not a provider billing hard cap.

Runtime tool traces are not a coding conversation. A genuine supplied coding
export can support the transcript category; hashes cannot prove its authenticity.
When all three categories exist, the report gives a local subtotal /70 and an
explicitly local normalized score. Otherwise it preserves missing categories.

## 6. Calibrate against observations without fitting a winner

Our original public-winner review did not match the official category scores.
The code-rigor emphasis had drifted; output also used a local qualitative method
rather than private official gold. We preserved those estimates and made the
observed gap visible instead of adding an offset.

`calibration/protocol-v1.json` freezes criteria, anchors, evidence requirements and
selection/leakage limitations before new ratings. The separate August output
amendment was frozen after recovering original context/media, before output
ratings. `calibration.py` verifies protocol/review identities, recomputes criterion and
partial-output arithmetic, and generates comparisons. `calibration_audit.py`
compares independently frozen decisions with separately held public labels.
Official targets live in the dataset/report, not the neutral review bundles. Targets were already known to this project, so this is not a truly blind
holdout. Two selected entrants do not validate statistical error or rank accuracy.

```sh
python -m orchestrate_eval calibration report --dataset calibration/dataset-v1.json --report-dir reports/calibration
```

This recomputes weighted points, missing-category coverage and signed/absolute
observed gaps from frozen reviews. It applies no offset or learned scale. New
reviews can be created with `calibration export`, checked with `freeze-review`
and reverified against the original source bundle with `calibration verify`.
Full third-party source/log bundles are kept outside the published repository;
the committed reviews retain short evidence references and source hashes.
See [CALIBRATION.md](CALIBRATION.md) and [the earlier official comparison](OFFICIAL_SCORE_COMPARISON.md).

A separate fresh label-hidden public-sample audit got 27/27 action and 24/27 type
decisions correct, with three voice cases unknown. That establishes useful basic
decision agreement on this sample, not official output-score calibration. Its
type-boundary findings and unchanged predictions are preserved in CALIBRATION.md.

## 7. Keep coding-agent integration distinct from task-agent quality

`coding_agent.py` gives an installed Codex CLI a scaffold repair task, preserves
the actual development events/patch, then benchmarks the produced task agent.
That is Codex as a developer, not Codex answering every support ticket.

The real local CLI attempt failed at read-only initialization before any model
turn. The process-to-artifact-to-runtime wiring is tested with an explicitly
synthetic CLI fixture; that is not a live Codex performance result. See
[CODING_AGENTS.md](CODING_AGENTS.md). A successful narrow repair smoke would still
not establish comprehensive contest readiness.

## 8. Verify and publish a reproducible implementation

```sh
python -m unittest discover -s tests -v
python -m compileall -q orchestrate_eval examples tests
python examples/replay_benchmark_scores.py
python -m orchestrate_eval calibration report --dataset calibration/dataset-v1.json --report-dir reports/calibration
```

CI runs the standard-library tests and offline replay on Python 3.10/3.12/3.13.
Clean-copy wheel installation is tested outside the checkout. A green CI result
proves the included tests passed, not live model availability, competitor runtime,
official hidden labels or score calibration.

## Release-day October adaptation checklist

1. **Freeze the actual edition.** Save the official spec, rules, sample/data and
   retrieval timestamp; hash files. Check weights, permitted architectures,
   submission contracts and any rubric override before reusing May/August aids.
2. **Inspect the data before building a solution.** Record headers, enums, IDs,
   missing fields, media/context links and train/sample/final overlap. Do not
   assume row order or an ID suffix encodes a label. Keep official/private data out
   of public uploads unless redistribution is explicitly allowed.
3. **Separate development from untouched evaluation.** Use independent sample
   labels where available; keep candidate predictions out of the reference. Freeze
   an evaluation split before changing prompts. If labels are absent, report
   grounded judgments with their limitations instead of inventing exact accuracy.
4. **Make one working adapter.** Reuse execution/report plumbing. Change only the
   task-facing protocol, tools and output schema needed for the released problem.
   Get a tiny actual run working before broad optimization.
5. **Add a versioned checker/casepack.** `benchmark cases --output my-cases.json`
   gives an editable reference template. Replace its policies/cases with the new
   task, or implement a task-specific semantic checker when its tools/outputs are
   different. Keep facts, actions, useful explanations and evidence grounding
   separate. Test an obviously wrong answer and a contradictory answer first.
6. **Add relevant safety/failure cases.** Derive them from that task: instruction
   injection, unsupported requests, ambiguous evidence, missing tool/media data,
   malformed output, unauthorized actions and applicable language variants. Do not
   count an error envelope as a test of damaged JSON transport.
7. **Preserve development evidence from the beginning.** Keep the original coding
   export, actual code/config versions, model settings and every run. No fabricated
   log, synthetic transcript submission, best-run cherry-picking or gold lookup.
8. **Check allowance before model calls.** Set explicit deadlines/cost contracts,
   use one small smoke first and preserve the required quota reserve. Unknown
   allowance is not permission for a large batch. Use an isolated trusted setup;
   the harness itself does not contain untrusted code.
9. **Run smoke, negative controls and regressions.** Confirm IDs align, schema is
   correct, tools are really used, wrong/unsafe answers lose points, evaluator
   errors remain unknown and source/transcript review cites actual evidence.
10. **Produce the report and inspect failures.** Compare identical references and
    settings, retain all repeats, review uncertain cases, and label local
    estimates honestly. Check the final archive/entry point/output and actual
    edition rules. Do not mistake a local /70 estimate for official ranking.

The fastest safe adaptation is to reuse the runner, evidence binding and report
interfaces while replacing the task references/checker. Reusing an old task's
answers or its score weights without checking the new contract is not adaptation.
