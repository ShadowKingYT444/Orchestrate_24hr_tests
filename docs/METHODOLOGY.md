# Methodology and limits

This repository is an independent evaluation tool, not the proprietary HackerRank grader. The original evaluate/archive commands provide readiness diagnostics; benchmark adds actual agent execution, reference-backed invariants and evidence-based numerical model/human judging. Voice/interview is intentionally excluded. Published generic weights are30/30/10 for code/output/coding transcript and30 for interview. Local category estimates and a complete non-voice subtotal/70 are available after required semantic/rubric reviews; the aggregate official score remains unknown. Edition-specific instructions take priority. See BENCHMARK.md for scoring caps, unknown handling and executed evidence.

## Evidence levels

- Objective: exact comparisons, schema constraints, syntax parsing, file digests, archive limits. A pass applies only to the named condition.
- Proxy: presence of README/dependency declarations/tests/lockfile, declared transcript provenance. These do not establish quality, reproducibility or truth.
- Subjective: source and transcript review ratings require cited evidence; user/judge claims remain advisory. The tool does not verify cited line references automatically.
- Unknown: hidden accuracy labels, semantic correctness not implemented by a plugin, transcript authenticity, provider usage/costs absent telemetry, official scores.

`pass` never means a winner prediction. `incomplete` is expected when unknown objective dimensions remain. Failing proxies appear in the report but do not independently cause an objective failure. Bad task configuration and malformed JSON inputs exit 2; failed objective checks (including invalid CSV contracts) exit 1. Incomplete evidence also exits 2; inspect the message/report to distinguish it from a configuration error.

## Threat model

Offline evaluation never executes candidate code or imports its modules. Source parsing is bounded per file and count, but static inspection is not proof of harmlessness. Reports escape HTML, perform no remote fetches and contain no embedded scripts. Avoid sharing reports/logs without inspecting potentially sensitive candidate contents.

Trusted subprocess execution is opt-in. Timeouts, log-size sampling and POSIX process-group termination are not a security boundary. Fast writers can temporarily exceed disk limits; detached descendants can escape; memory and network are not constrained. Use independently configured isolation for untrusted code. The runner deliberately does not inherit API keys or a full environment.

ZIP policy: <=50,000,000 compressed bytes, <=200,000,000 expanded bytes, <=5,000 members, ratio <=200. These expansion/member/ratio restrictions are local safety choices, not official contest rules. Reject unsafe names, symlinks/special files, duplicate/case collisions, encryption, unknown compression, nested archives, suspected credential filenames, CRC corruption, ZIP64/multivolume and prefixed/trailing payloads. Nested archive rejection can reject legitimate bundles; package plain source instead. No claim of malware detection or complete secret discovery. Atomic extraction API refuses an existing target and requires a trusted destination parent; it never runs extracted files.

## Honest transcripts and review

The relevant transcript is the actual AI coding-tool development conversation. Runtime traces cannot substitute. Do not fabricate or lengthen logs to improve scores. Normalize an export without altering content and retain original provenance. A SHA-256 digest proves only file identity. Useful review evidence: decisions tied to requirements, specific implementation guidance, tests and corrected failures, and genuine safety/edge-case discussion. Verbosity earns nothing here.

The published May code rubric (architecture 30, prompts/tools 30, robustness 25, rigor 15) and transcript rubric (direction 35, specificity 25, iteration 25, safety 15) are historical aids, not automatically applicable to another edition. This tool intentionally does not map generic keyword checks to these points.

## Validation

Unit tests use synthetic data only: passing/failing baseline outputs, malformed JSON/CSV, duplicate keys/IDs, timeout/nonzero exit/log overflow, hostile ZIPs and authored Git-repository fixtures. No hidden tests, private answers, contest dataset or competitor code are bundled. June/September structural fixtures are authored for this suite. Historical validators explicitly leave task semantic correctness unknown. CI executes only our own tests and toy subprocesses, never uploaded candidate harnesses. Optional `validate-public` independently reads pinned real public artifacts after the user clones them; Git is required for its provenance checks. See REAL_WORLD_VALIDATION.md for actual results, boundaries and reproducible commands.

## Reproducibility and eligibility

No runtime dependencies. Python version and platform can affect subprocess handling; CI tests multiple supported Python versions on Linux. Pin your own harness dependencies and preserve config/dataset/output hashes and usage metadata. Official general guidance says individual/original work; preparation/reuse permissions are not sufficiently explicit to guarantee any prebuilt solution is allowed. Confirm the actual edition rules before submission.

## Local metric and resource policies

Check counts are grouped by evidence type and category; no pass ratio is used as a quality score. Different profiles have different check granularity, so counts are not comparable grades. `labelled_csv` accuracy uses explicitly supplied reference strings. Missing reference IDs count as mismatches; unexpected candidate IDs fail coverage without changing the reference-label denominator. Duplicate IDs are ambiguous and produce no metrics. Exact matches do not establish semantic correctness or label quality. At most 1,000 case details (mismatches first) and 200 sorted confusion entries per field are embedded, with explicit truncation flags/counts. Aggregates include every reference row.

Input limits: JSON, CSV and individual Python files <=5,000,000 bytes; CSV <=50,000 data rows and 256 columns; labelled metrics <=128 fields and column names <=128 characters; JSON nesting <=128. September decimals admit up to 100 significant digits and exponents from -1000 through 1000, with exact remainder arithmetic within these local limits. Symlinks and non-regular files are refused. Comparison reports have a separate 50,000,000-byte input limit. Snapshots and digests are bounded, but these checks do not secure concurrent hostile filesystem changes. Digests bind bytes, not execution provenance.

CLI source-submission hygiene additionally requires a README and rejects files under `.git`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `build`, `dist`, `dataset`, or `datasets`, plus Python bytecode. These are conservative local name policies, potentially stricter than edition rules. They cannot identify every supplied dataset or generated artifact under arbitrary names.

## Official-score calibration and genuine coding agents

The original `local-audit-v1-preserved` numerical code review used an experimental-rigor emphasis that differed from published May engineering rigor. New judge bundles use `may26-published-aid-v2` with the published criterion meanings, while original scores remain unchanged. This is rubric correction, not a fitted numeric calibration. [Official-score comparison](OFFICIAL_SCORE_COMPARISON.md) records material gaps and unverified server-artifact identity. The `evaluate` advisory audit remains separate and unweighted.

[Coding-agent integration](CODING_AGENTS.md) distinguishes developer coding events from task-agent runtime. The real installed Codex attempt failed before a model turn. Unit-mocked integration success does not establish live Codex behavior or complete benchmark coverage.
