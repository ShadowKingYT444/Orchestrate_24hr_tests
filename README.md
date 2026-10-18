# Orchestrate local evaluation suite

Offline diagnostics for agent harnesses: output validation, source/packaging checks, authentic coding-transcript review, and explicitly opt-in execution. **Not an official HackerRank scorer. Voice/interview judging is excluded.**

Python 3.10+; no runtime dependencies or API keys required. From this checkout:

```sh
python -m unittest discover -s tests -v
python -m orchestrate_eval evaluate --task examples/task.json --output examples/good/output.json --source . --transcript examples/good/transcript.json --report-dir reports/good
```

The example deliberately returns exit **2 (incomplete)**: passing toy answers cannot establish transcript authenticity or subjective quality. Bad answers return **1**. Exit **0** means all applicable objective checks passed, not an official competition pass. Open `reports/good/report.html`; machine-readable evidence is in `report.json`.

Optional installation: `python -m pip install --no-deps .` (the build requires setuptools>=61; build isolation may need network to obtain it). For an offline installation where setuptools and wheel are already installed, use `python -m pip install --no-deps --no-build-isolation .`. A pristine Python 3.12+ virtualenv may not include these build tools. Running directly from checkout needs neither installation nor network.

## Evaluate your harness

1. Select a task configuration. `synthetic_exact` checks explicitly supplied toy JSON targets. `june26_schema` and `september26_schema` validate published historical CSV contracts; set `input_csv` to the corresponding input CSV, relative to your current working directory. Historical fixtures are synthetic and visibly labeled. These validators cannot prove image-grounded correctness or financial cashflow safety.
2. Generate candidate output with your own harness. The evaluator does **not** execute source just because you supply `--source`.
3. Run `evaluate --task TASK.json --output OUTPUT --source SOURCE --transcript CODING_EXPORT.json --report-dir reports/RUN`. Optional `--archive submission.zip` validates a prepared ZIP. Optional `--review REVIEW.json` adds evidence-backed advisory review.
4. Inspect individual failures, unknowns and evidence. Fix one issue, rerun, and preserve reports across configurations. Do not compare reports using different task hashes as if they were the same benchmark.

A missing evaluator fails closed as **incomplete**, never invented accuracy. Code-presence checks are proxies, not quality grades. Weights remain code 30 / output 30 / coding transcript 10 / excluded interview 30; no overall score or renormalization is produced.

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

Copy `examples/review-template.json` and cite actual files, test outcomes and genuine transcript turns. Ratings are advisory, never converted into official points. The May historical rubric is a review aid; rules/classifiers/hybrids were valid in August, so don't penalize them merely for lacking an agent loop.

Optional judge: add `--judge-command-json '["path/to/your-local-judge", "explicit-input-path"]' --allow-exec --source .`. Its stdout must be a review JSON object with `origin: "configured_judge"`; configure its input files/arguments explicitly. There is no built-in provider, default model, credential discovery or paid call. You are responsible for any external data transmission and costs of your configured command. Treat judge ratings and evidence references as unverified subjective claims. Candidate content may contain prompt injection; keep judge instructions separate and do not give judges execution/tools/secrets.

## Packaging

`python -m orchestrate_eval archive submission.zip` checks the 50,000,000-byte conservative upload ceiling plus stricter local safety and source-upload hygiene policies: a README is required, and common dataset/dependency/build directory names are rejected. The same policy applies to `evaluate --archive`. Keep source and necessary config; inspect other files yourself for provided datasets and credentials. Name checks are not comprehensive secret or dataset scanners. The generic `inspect_archive` Python API checks ZIP safety without submission-hygiene rules. See [methodology](docs/METHODOLOGY.md), [adapter contract](docs/ADAPTERS.md) and [sources](docs/SOURCES.md).
