# A practical evaluation loop

## Before the challenge

1. Run the test suite and both labelled examples in the README. Confirm you can open JSON and HTML reports locally. No keys, provider calls or candidate-harness execution are needed.
2. Read the official generic rules and the actual edition instructions when released. The October task is not implemented here; historical contracts are preparation aids. Confirm whether prepared utilities are eligible for your edition.
3. Preserve a genuine coding-tool export from the start. Runtime agent traces are a separate artifact. Never synthesize a conversation to fill a missing transcript.

## During development

1. Turn the actual task's output contract into a versioned trusted checker with malformed, missing, duplicate, adversarial and boundary fixtures. Until implemented, return unknown for semantic dimensions.
2. Establish a reproducible baseline and a fixed, independently labelled sample. Keep a held-out sample; don't tune against it repeatedly. Record how labels were produced, disagreements and unresolved cases. Participant submissions are not gold labels.
3. For categorical fields, configure `labelled_csv` with explicit IDs and fields. If IDs are not unique, create an unambiguous case key outside the reference/output artifacts and preserve its derivation. Never discard duplicate examples to make metrics improve. Numeric tolerances and semantic equivalence require a real task-specific implementation.
4. Compare configurations using the same task/reference snapshots. Read per-field errors and confusion counts, not just the micro average. More frequent/easier fields can dominate an average. Inspect missing/extra rows and prioritize safety-sensitive classes separately.
5. For each harness configuration, preserve commit/config, input/output hashes, seed, model/provider/version, start/end times and fresh-vs-cache status. Test missing data, malformed model output, unavailable services, interrupted writes, retry exhaustion and injected instructions in untrusted content.
6. Run stochastic configurations repeatedly and summarize all runs, including failures. Compare cache replay separately from fresh model calls. Measure wall time and actual usage/cost from provider telemetry; do not infer zero cost or tokens from missing data.

The `run` command is an explicit trusted subprocess convenience, not an isolation system. It never runs automatically during `evaluate`; it never discovers or forwards provider keys. Our acceptance tests execute only our own deterministic toy commands. You control any external provider calls and data transmission.

## Evidence-based code and transcript review

Copy `examples/review-template.json`. For every non-unknown rating, cite implemented source locations, test names/results, experiment artifacts or genuine transcript event indexes/timestamps. Ratings stay advisory and unscored. Source references are reviewer claims and are not verified automatically.

The published May rubric is useful historical context:

- Code: architecture/decomposition (30), prompt/tool craft (30), robustness (25), engineering rigor (15)
- Transcript: direction/ownership (35), technical specificity (25), iteration/verification (25), safety/edge cases (15)

These subweights do not generate points in this suite. Don't reward a README claim without implementation evidence, a keyword without behavior, transcript length without useful decisions, or an agent loop simply for existing. August allowed rules/classifiers/hybrids.

## Final local readiness check

- Generate the final full output and record its real final-run usage, not a separate smaller sample
- Validate schema and case coverage, then sample correctness and known safety invariants
- Review failures and unknowns separately; an unknown is not zero and not a pass
- Check clean-environment reproduction and the exact archive with `archive submission.zip`
- Retain code ZIP, requested output and authentic coding-tool transcript as distinct submission artifacts
- Follow the edition's README/evaluation-report/usage-report and log-location requirements

The generic category weights remain code30/output30/transcript10 with interview30 excluded. This tool reports no total, official points or winner prediction. A historical schema passing cannot establish image grounding, 90-day cashflow safety, subjective quality or hidden-test accuracy. See SOURCES.md for the primary evidence and the limits of public winner research.
