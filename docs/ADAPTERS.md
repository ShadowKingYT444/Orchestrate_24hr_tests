# Adapter and plugin contracts

## Candidate execution

A harness command accepts explicit task/input/output locations; exits zero only after writing complete output. Keep inputs immutable; output into a fresh run directory. A suggested bundle is `output.csv` or `output.json`, `usage.json`, and `runtime.jsonl`. Runtime logs are not the coding transcript.

Record dataset SHA-256, configuration/version, commit, seed where supported, start/end UTC, model/provider/version, request counts, input/output/cache tokens, errors/retries, and actual billed or clearly estimated costs with rate/date source. Unknown fields must remain null. Separate fresh-model runs from cached replay. Do not log credentials or sensitive input payloads by default. Keep original coding exports private unless you explicitly intend to submit them.

`examples/adapter.py` is a deterministic toy demonstrating the boundary, not a proposed challenge solution. The CLI will not automatically run external harnesses or install their dependencies.

## Output plugins

`orchestrate_eval.checks.BUILTIN_PLUGINS` maps built-in JSON plugin names to `(candidate_object, task_object) -> list[check]`. A check is `{name, status: pass|fail|unknown, kind: objective|proxy|subjective, evidence: list[str]}`. CSV historical plugins use `historical.evaluate_historical(output_path, task)`. `metrics.evaluate_labelled(output_path, task)` returns `(checks, metrics)` for the explicit `labelled_csv` profile; its metrics are exact local-label comparisons only.

Add a trusted Python module and register it explicitly in code to support a new task. Arbitrary plugin paths/imports from submitted task JSON are intentionally unsupported. Tests must include valid, malformed, missing, duplicate, adversarial and boundary cases. Return unknown for unimplemented semantic dimensions; never substitute schema validity for task accuracy. Prefer independently authored expected outputs and per-field metrics. Never use competitor submissions as gold answers.

For October, wait for published task instructions, then create a versioned profile and checker. The historical rules can change. No October solution or hidden data is included.

## Comparing configurations

Use identical dataset/config hashes and fixed sample definitions. Compare at least two strategies where the edition requests it. Measure successful output checks, errors/timeouts, wall time, actual API usage and per-case outcomes. Rerun stochastic configurations and report distributions rather than the best run. Keep replay results separate from new-model results. Review architecture and implementation with evidence; keyword presence does not establish quality.
