# Orchestrate agent benchmark and local judge

Run actual agents on reference-backed tasks, retain real tool traces, judge answer meaning, and estimate code/output/coding-transcript category points. **Local estimates, not the proprietary HackerRank grader. Interview is excluded.**

The executed, independently judged examples separate a competent policy agent from an unsafe one:

- Competent: code 21.38/30 + output 26.56/30 = **47.93/60 known**
- Unsafe: code 4.50/30 + output 5.25/30 = **9.75/60 known**

These come from real 20-case agent runs plus evidence-backed model review, not file checks or invented transcript scores. Genuine coding transcripts were absent; that 10-point category stays unknown. A complete genuine transcript review produces the non-voice subtotal/70 and an explicitly local normalized/100 estimate. [Scoring, runtime protocol and full workflow](docs/BENCHMARK.md).


Important calibration result: the original local review gave the May winner code **17.81/30** and output **26.08/30**, while the official leaderboard reports **26.4/30** and **22.8/30**. These are materially different assessments, and public artifacts are not verified server uploads. [Exact comparison and rubric-version audit](docs/OFFICIAL_SCORE_COMPARISON.md).

A genuine Codex developer adapter now repairs a scaffold, preserves its coding events, then benchmarks its produced support agent. The installed real CLI was attempted here but failed at read-only state initialization **before any model turn**; mocked wiring tests are separate. [Codex integration, actual evidence and coverage gaps](docs/CODING_AGENTS.md). The 20 authored cases are a narrow development benchmark, not comprehensive competition validation.

Quickly replay the preserved actual runs and native model judgments without keys or paid calls:

```sh
python examples/replay_benchmark_scores.py
```

Open reports/demo-comparison/comparison.html. To execute a fresh agent run:

```sh
python -m orchestrate_eval benchmark run --allow-exec --cwd . --command-json '["python","examples/agents/strong.py"]' --split all --report-dir reports/fresh
python -m orchestrate_eval benchmark judge-export --source examples/agents/strong.py --benchmark-report reports/fresh/benchmark.json --output reports/fresh/judge-bundle.json
```

Have your chosen model/human review that bundle, then use benchmark judge-import. Or use the opt-in compatible HTTP/local-worker judge adapter. A one-command run can add --source, --transcript, --judge-config and --allow-judge-network for configured automatic model grading. No provider is called by default. Use --casepack for your own frozen reference tasks; the included policy world is a development benchmark, not universal contest accuracy.

The **real May winner's public agent** was also qualitatively graded: all 27 Python files and all 29 saved outputs against the supplied corpus, with numerical code/output estimates and exact evidence. That is source/saved-output review, not a live paid rerun. [Real-agent grading results](docs/REAL_WORLD_JUDGING.md).

## Build, calibration and October adaptation

[How this was built from scratch, with the fast October adaptation checklist](docs/BUILD_AND_ADAPT.md) covers the initial project tree, build order, function/data contracts, scoring, commands and release-day changes.

[The frozen calibration study](docs/CALIBRATION.md) corrects published-rubric interpretation without fitting offsets. May code's observed gap falls from 8.5875 to 3.30 points; an external August project has code/log gaps of +1.35/−1.00. **The external output comparison fails: its local contribution interval is 22.4080–24.5898/30 versus official 13.8. Output estimates are not calibrated official-score or rank predictions.** A separate label-hidden public-sample audit checks the semantic judge's action/type decisions. Original judgments and failed results remain available.

The fresh sample judge matched **27/27 actions** and **24/27 message types**; three voice cases remain unknown. [Frozen audit and disagreements](calibration/label-audit-results-v1.md). Replay both studies offline with `python examples/replay_calibration.py`.

## Artifact checks and historical profiles

The original offline preflight tools remain useful alongside runtime judging: schema/coverage checks, archive safety and coding-export provenance. [Original real-artifact calibration](docs/REAL_WORLD_VALIDATION.md).

Python 3.10+; no runtime dependencies or API keys required. From this checkout:

```sh
python -m unittest discover -s tests -v
python -m orchestrate_eval evaluate --task examples/task.json --output examples/good/output.json --source . --transcript examples/good/transcript.json --report-dir reports/good
```

The example deliberately returns exit **2 (incomplete)**: passing toy answers cannot establish transcript authenticity or subjective quality. Bad answers return **1**. Exit **0** means all applicable objective checks passed, not an official competition pass. Open `reports/good/report.html`; machine-readable evidence is in `report.json`.

Optional installation: `python -m pip install --no-deps .` (the build requires setuptools>=61; build isolation may need network to obtain it). For an offline installation where setuptools and wheel are already installed, use `python -m pip install --no-deps --no-build-isolation .`. A pristine Python 3.12+ virtualenv may not include these build tools. Running directly from checkout needs neither installation nor network.

## Evaluate your harness

1. Select a task configuration. `synthetic_exact` checks explicitly supplied toy JSON targets. `may26_schema`, `june26_schema` and `september26_schema` validate published historical CSV contracts; set `input_csv` to the corresponding input CSV, relative to your current working directory. Bundled historical fixtures are synthetic and visibly labeled; the separate public calibration reads actual third-party artifacts from your pinned checkout. These validators cannot prove safe routing, image-grounded correctness or financial cashflow safety.
2. Generate candidate output with your own harness. The evaluator does **not** execute source just because you supply `--source`.
3. Run `evaluate --task TASK.json --output OUTPUT --source SOURCE --transcript CODING_EXPORT.json --report-dir reports/RUN`. Optional `--archive submission.zip` validates a prepared ZIP. Optional `--review REVIEW.json` adds evidence-backed advisory review.
4. Inspect individual failures, unknowns and evidence. Fix one issue, rerun, and preserve reports across configurations. Do not compare reports using different task hashes as if they were the same benchmark.

For the original evaluate command, a missing evaluator fails closed as **incomplete**, never invented accuracy. Code-presence checks are proxies, not quality grades. That preflight command produces no aggregate score. The separate benchmark/judge workflow produces explicitly local category estimates and a complete subtotal/70 only when all required reviews exist.

## Measure your own labelled sample

`labelled_csv` compares exact CSV strings against a reference you explicitly supply. It supports any task with unique case IDs and independently labelled fields. It reports per-field accuracy, confusion counts, exact-row accuracy, missing/extra IDs and case mismatches. References are local labels, never assumed to be official or correct. Do not use another participant's predictions as ground truth.

Try both synthetic configurations from the repository root (the first exits 1 for its mismatch, the second exits 2 because source/transcript evidence is absent):

```sh
python -m orchestrate_eval evaluate --task examples/labelled/task.json --output examples/labelled/candidate-a.csv --label baseline --report-dir reports/a
python -m orchestrate_eval evaluate --task examples/labelled/task.json --output examples/labelled/candidate-b.csv --label revised --report-dir reports/b
python -m orchestrate_eval compare reports/a/report.json reports/b/report.json --report-dir reports/comparison
```

Open `reports/comparison/comparison.html`. The synthetic baseline matches 5/6 fields; the revised fixture matches 6/6. These demonstrate the metrics, not challenge performance. Comparisons reject different task/reference hashes. They do not establish identical runtime settings or a fresh model run.

Adapt `examples/labelled/task.json`: set `reference_csv`, `id_column`, `fields` and an honest `reference_description`. Paths resolve relative to your current working directory. Use exact-label metrics for categorical fields; numeric tolerances, equivalent explanations, image grounding and financial safety need a task-specific checker. Aggregates cover all reference rows. Reports embed up to 1,000 case details (failures first) and 200 confusion entries per field; truncation is explicit. Local check-count scorecards separate objective checks, proxies and subjective review and are never quality scores. See [the practical workflow](docs/WORKFLOW.md).

## Explicit trusted command execution

```sh
python -m orchestrate_eval run --allow-exec --cwd . --timeout 10 --command-json '["python","examples/adapter.py","--output","reports/candidate.json"]' --report-dir reports/run
```

Create the output parent directory first (`mkdir -p reports`). Command arguments are a JSON array, no shell interpolation. `run.json` records exit status, wall time, timeout and bounded log captures. Costs, token counts and peak memory are **unknown**, not zero. The runner passes a small environment allowlist; API credentials are not inherited automatically.

**This is not a sandbox.** Only run trusted code here. Candidates can access your filesystem/network, spawn detached children or exhaust memory/disk. Timeout and sampled log limits are best-effort diagnostics, not isolation or hard disk bounds. Run untrusted submissions in a disposable VM/container configured with no credentials, no network, read-only mounts and OS resource limits. This suite does not provision that isolation.

## Coding transcript and advisory judging

Use genuine development-tool conversation exports, not agent runtime logs. Normalize a copy to `{ "provenance": {"source":"tool/export format", "exported_at":"ISO timestamp", "run_id":"identifier"}, "events":[{"timestamp":"ISO timestamp","role":"user|assistant|tool","content":"original text"}] }`. Keep the original export separately. Hashes bind files, not authenticity. Never fabricate an export or submit `examples/good/transcript.json` (explicitly synthetic).

Copy `examples/review-template.json` and cite actual files, test outcomes and genuine transcript turns. Ratings are advisory, never converted into official points. This original advisory template is an unweighted general engineering audit. The separate versioned benchmark judge uses the published May dimensions; rules/classifiers/hybrids were valid in August, so choose the actual edition instead of silently applying May-specific architecture expectations.

Optional judge: add `--judge-command-json '["path/to/your-local-judge", "explicit-input-path"]' --allow-exec --source .`. Its stdout must be a review JSON object with `origin: "configured_judge"`; configure its input files/arguments explicitly. There is no built-in provider, default model, credential discovery or paid call. You are responsible for any external data transmission and costs of your configured command. Treat judge ratings and evidence references as unverified subjective claims. Candidate content may contain prompt injection; keep judge instructions separate and do not give judges execution/tools/secrets.

## Packaging

`python -m orchestrate_eval archive submission.zip` checks the 50,000,000-byte conservative upload ceiling plus stricter local safety and source-upload hygiene policies: a README is required, and common dataset/dependency/build directory names are rejected. The same policy applies to `evaluate --archive`. Keep source and necessary config; inspect other files yourself for provided datasets and credentials. Name checks are not comprehensive secret or dataset scanners. The generic `inspect_archive` Python API checks ZIP safety without submission-hygiene rules. See [methodology](docs/METHODOLOGY.md), [adapter contract](docs/ADAPTERS.md) and [sources](docs/SOURCES.md).
