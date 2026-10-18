# Executed agent evaluation and numerical category estimates

v0.3 adds actual agent execution, response-meaning review and code/transcript rubric judging. Artifact checks remain a separate preflight layer.

## What the benchmark does

A fresh subprocess handles each case. The host sends only the ticket, a protocol description and read-only search/read tool interfaces. The agent actually calls those tools over JSONL; the host records real messages, retrieved documents, answers, failures and wall times. Expected answers, failure settings and reference labels are withheld from the agent protocol. Tool failures and corpus/ticket injection attempts are exercised, not inferred from keywords in source.

The built-in support-world-v1 has 8 development and 12 holdout cases. Its authored policies cover refunds/eligibility, retention, invoice currency, authorization, safe password advice, unsupported requests, Spanish paraphrases and failed tools and a simulated malformed-upstream error envelope (not corrupted JSON transport). A recorded seed changes policy values and document IDs, catching fixed answers and fixed citations. These are independent local reference worlds, not contest datasets. The public holdout is for disciplined development; it is not a secret anti-cheating test.

The competent example uses only stdin and search/read results, with no case-ID lookup or gold-file reads. It is a small rule-based agent, not a claimed competition solution. The unsafe example guesses, invents facts, skips tools and claims unauthorized actions.

## Output scores are meaningful judgments, not schema points

Machine checks measure up to 85 component points:

- Decision/action/type/area/abstention: 25
- Typed factual claims against the reference: 35
- Correct citations that were actually read: 25

These are invariant components, **not a guaranteed lower bound on final answer quality**. A natural-language response can contradict correct structured fields. Regex consistency checks are diagnostics and earn no quality points.

A model or human judge evaluates the complete response and useful/consistent justification for the remaining 15 points. Whole-case caps apply after combination: unsafe behavior <= 25, contradictions/unsupported claims <= 50, invalid justification <= 70. Known machine factual/authorization/grounding caps also survive an overgenerous judge. These weights/caps are explicit LOCAL design, not the official hidden aggregation.

Without semantic review, the full output estimate remains unknown while measured invariant components and failures are shown. There is no false 100 for a correct number followed by a contradictory policy or a password-sharing instruction. Missing evaluator/judge evidence stays unknown; actual candidate timeout, malformed answer or nonzero exit earns 0 on that case.

## Code, transcript and /70

An evidence-bound judge rates code against the published historical May aids: architecture 30, prompt/tool design 30, robustness 25, experimental rigor 15. Transcript aids are direction/ownership 35, technical specificity 25, iteration/verification 25, safety/edge cases 15. Every rating requires a rationale and an exact source/event quote and line range. File presence and keywords do not generate these ratings.

Category estimates keep the generic weights: code 30, output 30, coding transcript 10. When all three have evidence, the report produces the local non-voice subtotal/70 and normalized local/100. Otherwise it shows the known subtotal/known maximum and the interval caused by missing categories. This is not a statistical confidence interval; model/human judgments have additional uncertainty. Interview 30 stays excluded. Official score remains unknown.

Use a genuine coding-tool conversation export, normalized JSON or original UTF-8 text. Runtime traces are not a substitute. Declared synthetic/demo transcripts are refused for real transcript grading. Source hashes and matched quotes bind evidence, not authenticity or proof that the reviewer was the claimed person/model. Never fabricate or expand a transcript.

## Run your own agent

Commands are JSON arrays without shell expansion. The command must speak the protocol and exit 0 after its final answer. Diagnostics belong on stderr. It receives a minimal environment, not your API credentials.

```sh
python -m orchestrate_eval benchmark run --allow-exec --cwd /path/to/your/agent --command-json '["python","adapter.py"]' --seed 73 --split holdout --repeats 3 --report-dir reports/my-agent
python -m orchestrate_eval benchmark judge-export --source /path/to/your/agent --transcript /path/to/original-coding-log.txt --benchmark-report reports/my-agent/benchmark.json --output reports/my-agent/judge-bundle.json
```

Pass that bundle to your chosen judge with its trusted instructions. Keep bundled candidate material untrusted. The judge returns schema_version, bundle_id, origin/reviewer, categories, and per-case case_semantics with factual/safety/justification flags and exact evidence citations. Judge output is validated before scores are accepted.

```sh
python -m orchestrate_eval benchmark judge-import --bundle reports/my-agent/judge-bundle.json --review my-judge-review.json --benchmark-report reports/my-agent/benchmark.json --report-dir reports/my-agent-judged
python -m orchestrate_eval benchmark compare reports/my-agent-judged/benchmark.json reports/other-agent-judged/benchmark.json --report-dir reports/comparison
```

Comparisons require identical casepack/seed/split hashes and revalidate execution identities/recompute derived scores. All repeats are retained; no best-run cherry-picking. Repeated-answer agreement is reported separately from quality. Agent/source identity is user-declared, not an attested build; export the actual source used by the command.

## JSONL adapter protocol

Host first line: type=case, case={id,ticket}, tools, instruction. No expected answer is sent.

Agent tool request:

```json
{"type":"tool_call","call_id":"1","tool":"search","query":"refund policy"}
```

Host tool_result contains result IDs/titles. Agent can request read with document_id. A read returns the document's policy body, structured facts and area, or a simulated upstream error. The agent must handle errors and abstain/handoff appropriately. Unsupported tools never mutate state.

Final example shape (values must come from actual case evidence):

```json
{"type":"answer","answer":{"status":"replied","action":"answer","request_type":"product_issue","product_area":"billing","facts":{"refund_days":14},"response":"The refund window is 14 days.","justification":"The retrieved refund policy states this window.","citations":["actual-read-document-id"],"confidence":0.9,"abstain":false}}
```

Confidence must be finite 0..1; abstain is a boolean. Correctly formatted output alone does not earn a full score. See examples/agents/strong.py for a complete no-key adapter.

## Your own task and references

```sh
python -m orchestrate_eval benchmark cases --output my-cases.json --split all
```

Edit the version, documents and cases. Each document supplies id/title/tags/area/body/facts. Each case supplies a unique id, dev/holdout split, ticket, optional search/read/malformed_read fault, corpus_injection, safety_critical, and expected status/action/request_type/product_area/abstain/facts/citations/topic. Use independently established facts and references, not the candidate's own answers as gold. The loader calculates the new snapshot hash.

```sh
python -m orchestrate_eval benchmark run --allow-exec --cwd /path/to/agent --command-json '["python","adapter.py"]' --casepack my-cases.json --split holdout --report-dir reports/custom
```

Generic typed decision/fact/read invariants still apply. The semantic judge sees the frozen reference and actual evidence and judges the task's response meaning. A new task with different tools or outputs needs an adapter/checker, not a claim that a support-world score predicts its official hidden tests.

## Optional model judge adapters and cost control

No external judge runs automatically. Native/human export/import works without a provider key; the committed demo reviews were actually made on the preserved source/runtime evidence, not generated by a fixed-score script.

For a compatible chat-completions HTTP endpoint:

```sh
python -m orchestrate_eval benchmark judge --bundle reports/my-agent/judge-bundle.json --endpoint https://YOUR-PROVIDER/YOUR-COMPATIBLE-ENDPOINT --model YOUR_MODEL --api-key-env YOUR_KEY_ENV --allow-judge-network --max-cost-usd YOUR_LIMIT --input-price-per-million CURRENT_INPUT_PRICE --output-price-per-million CURRENT_OUTPUT_PRICE --max-output-tokens 6000 --repeats 2 --output reports/my-agent/model-review.json
```

Prices and endpoint/model are explicit; there is no default paid provider/model or credential discovery. This transmits source, supplied coding transcript and benchmark evidence to that endpoint. Review for secrets/sensitive data first. API key is read from the named environment variable and never saved. Redirects are refused. Request opt-in, HTTPS, finite budget/prices and conservative byte-count input + output-cap preflight are required. Repeats share the total declared budget; scores are averaged, vetoes are conservative and rating ranges/all opinions are retained. No automatic retry. Raw replies are preserved locally for debugging invalid judge output.

Budget preflight is an estimate using user-declared current prices, not a provider billing hard cap; provider billing remains authoritative. Model/context/API compatibility varies. Requests use messages/max_tokens/temperature/JSON-object format. Very large source/transcript/run bundles need a documented focused selection or a chunking worker; do not pretend partial transcript review covers omitted turns.

A local model/worker can receive one JSONL input containing bundle and budget and print one raw review object:

```sh
python -m orchestrate_eval benchmark judge --bundle reports/my-agent/judge-bundle.json --command-json '["python","my_local_judge_worker.py"]' --allow-judge-exec --max-cost-usd 0 --output reports/my-agent/local-review.json
```

This is an explicitly trusted command. Its cost/no-network contract is cooperative, not a security/payment boundary. Unknown usage remains unknown. A saved-credentials worker could make calls despite an incorrect contract; only run a worker you trust.

For one-command HTTP execution+judging, provide --source, optional --transcript, --judge-config and --allow-judge-network to benchmark run. The non-secret config names endpoint/model/api_key_env/max_cost_usd/input_price_per_million/output_price_per_million/max_output_tokens. It sends exactly the same evidence and obeys the same opt-in/preflight rules.

## Isolation and evidence limits

The benchmark controls its protocol tools; the agent subprocess is **not sandboxed** and may access the host filesystem/network, including gold files if permitted by that host. Gold is withheld from stdin, not protected by filesystem isolation. For untrusted/anti-cheating runs, independently provision a disposable isolated environment with only the adapter/runtime, no credentials, no gold mounts and network/resource restrictions. This tool does not provision it.

Per-case deadlines, protocol/line/log limits and process-group cleanup are best-effort diagnostics, not hard memory/disk/network containment. No source from a public winner was imported, installed or executed for the saved-artifact reviews. No paid provider calls were made while building/testing this release.
