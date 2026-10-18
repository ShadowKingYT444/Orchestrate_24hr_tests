# Frozen calibration study and its limits

The published code-rubric interpretation was corrected and checked against two
public projects. **The local output-quality method failed the external official-
score comparison. It must not be treated as a calibrated official-score or rank
predictor.** Original estimates, new judgments, failed results and missing
evidence are preserved rather than fitted to a winner.

## Category results

All values are weighted category contributions, not four unweighted /100 grades.
The full reproducible table is [results-v1.md](../calibration/results-v1.md), with
[machine-readable results](../calibration/results-v1.json).

| Case/category | Official | Original local | New protocol / external review | Observed absolute gap |
|---|---:|---:|---:|---:|
| Saai May code /30 | 26.4 | 17.8125 | 23.10 | 8.5875 before; 3.30 after |
| Saai May output /30 | 22.8 | 26.0819 | 26.0819, retained unchanged | 3.2819 |
| GodVilan August code /30 | 22.8 | No prior estimate | 24.15 | 1.35 |
| GodVilan August supplied log /10 | 9.8 | No prior estimate | 8.80, conditional on the presented log | 1.00 |
| GodVilan August output /30 | 13.8 | No prior estimate | Full point estimate unknown; contribution interval 22.4080–24.5898 | Interval 8.6080–10.7898 |

Saai's transcript is absent locally. Swayam's June public tree is explicitly
cleaned up and substitutes demo data, so it is context only, not a matched
calibration sample. Missing categories are never assigned zero.

The revised Saai code estimate is 3.3 points low while the unchanged output
estimate is 3.2819 high. Their near-matching subtotal is cancellation of opposite
category gaps, **not calibration success**. New code ratings also involve a fresh
reviewer and explicit anchors; the improvement cannot be causally attributed to
one rubric wording correction alone.

## What was frozen before new ratings

- [Base protocol](../calibration/protocol-v1.json): published May code/transcript
  criteria, local 0–100 anchors, 5-point intermediate steps, exact evidence,
  unweighted extra engineering audit and edition applicability
- [August output amendment](../calibration/protocol-v1-august-output.json): frozen
  after original context/media were recovered, before output ratings; local field
  weights and whole-case caps were declared in advance
- [Dataset/provenance](../calibration/dataset-v1.json): roles, pins, artifact
  correspondence, coverage and separately recorded official observations
- [Frozen reviews](../calibration/reviews/): original and revised judgments with
  hashes and short evidence; full third-party source/transcript bundles are not
  redistributed

Saai is a development re-review following a diagnosed criterion mismatch.
GodVilan is an external exploratory case from another edition. The project knew
the official values before this protocol; fresh review inputs omitted explicit
scores/rank, but this is not a truly blind holdout. Two selected entrants and
unverified server-upload byte identity cannot establish statistical calibration,
general error bounds or cross-edition rank accuracy.

The old code audit emphasized tests/CI/lockfiles under “experimental rigor.” The
published May engineering criterion instead emphasizes modularity, annotations,
environment-held secrets and manageable function size. We corrected that meaning
without changing category weights or fitting offsets. August explicitly allowed
rules/classifiers/hybrids; its architecture was judged for appropriate task fit,
not penalized merely for lacking a model-directed loop.

## Why the output result remains a failure

Two fresh native reviewers evaluated all 102 text/image rows against original
official context, including actual image pixels. The 8 voice rows were left
wholly unknown because the audio was not interpreted. Their contribution bounds
allow any 0–100 result for each unknown row; those rows are not graded zero.

The reviewed-row mean is 24.1654/30. Even the lower all-110 contribution bound is
well above the official 13.8. Reviewers identified invented/contradicted reasons
on 26 rows and irrelevant/generic reasons on 7, using the already-declared caps.
Those findings were derived from actual cases, not the author's later errata.
Neither caps nor field weights were tightened after viewing the result.

This qualitative field method is not the official hidden-label/adversarial
aggregation. The observed mismatch can reflect reference judgments, severity,
aggregation and artifact differences; the official aggregate does not reveal the
cause. No arithmetic offset can legitimately repair those unknowns. Code/log
ratings remain frozen even when later output review suggests additional risks.

## Separate official-labelled-sample judge audit

The [audit protocol](../calibration/label-audit-protocol-v1.json) was frozen before
a fresh reviewer received the public 30-row sample. All five output columns were
removed, including reasons/confidence/evidence IDs, not just action/type. The
reviewer received original input/context/images, no candidate output, no prior
reviews and no official entrant scores. Its raw independent predictions were
hashed before label comparison.

The frozen comparison found:

| Decision field | Correct / reviewed | Accuracy on reviewed | All-30 missing-decision interval |
|---|---:|---:|---:|
| Action | 27/27 | 100% | 90–100% |
| Message type | 24/27 | 88.89% | 80–90% |
| Both exact | 24/27 | 88.89% | 80–90% |

See [frozen audit results](../calibration/label-audit-results-v1.md),
[per-case comparisons](../calibration/label-audit-results-v1.json) and
[unchanged independent predictions](../calibration/reviews/august-sample-predictions-v1.json).
The [provenance/chronology record](../calibration/label-audit-provenance-v1.json)
records the label-free pack and raw prediction hashes, freeze-before-comparison
order and the limits of prompt-scoped rather than OS-attested isolation.

All three disagreements are type-only: sample_msg_002 was labelled `urgent`
instead of official `event`; sample_msg_005 `business_update` instead of `event`;
sample_msg_049 `personal` instead of `unknown`. Action decisions were correct.
These suggest separating delivery urgency from message taxonomy, not letting a
verified business sender alone determine type, and requiring positive evidence
before assigning a personal-message category. Those are development findings,
not case-ID substitutions or a validated new prompt. No predictions were revised
or rerun after comparison. A future changed judge needs its own version and new
evaluation evidence.

This audit measures exact action/type decisions by ID, joint correctness,
confusions and coverage. Three uninterpreted voice cases remain unknown. It does
not test an actual candidate, open-text answer quality, calibrated probabilities
or official /30 output points. Public-sample/pretraining exposure is not
controlled. See the frozen audit results and per-case disagreements linked from
the README; do not convert a good sample accuracy into a final-score prediction.

## Reproduce or extend the study

From the checkout, no key, model call, candidate execution or network is needed:

```sh
python examples/replay_calibration.py
python -m orchestrate_eval calibration report --dataset calibration/dataset-v1.json --report-dir reports/calibration
```

The replay recomputes criterion/output arithmetic and checks frozen file hashes.
It does not reload the original full source/logs. To recheck exact source quotes,
recreate the pinned, score-free source bundle and run:

```sh
python -m orchestrate_eval calibration export --source /path/to/neutral/source --protocol calibration/protocol-v1.json --edition may26 --output reports/new-bundle.json
python -m orchestrate_eval calibration freeze-review --bundle reports/new-bundle.json --review new-native-or-human-review.json --output reports/new-frozen-review.json
python -m orchestrate_eval calibration verify --bundle reports/new-bundle.json --review reports/new-frozen-review.json
```

Score-bearing README/results files must be removed from review inputs; arbitrary
source is not automatically guaranteed label-free. New reviews bind the exact
protocol and evidence. Preserve earlier versions; do not overwrite a failed
external check or silently relabel development evidence as held out.

For an original sample-file recheck, obtain the official repository at the pinned
commit rather than using another participant's output as gold:

```sh
git clone https://github.com/interviewstreet/hackerrank-orchestrate-august26 external/august26
git -C external/august26 checkout b2c4b904580c04cc3a66a82670b07838daf34a10
python -m orchestrate_eval calibration audit-labels --labels external/august26/dataset/sample_messages.csv --predictions calibration/reviews/august-sample-predictions-v1.json --protocol calibration/label-audit-protocol-v1.json --report-dir reports/original-sample-audit
```

Only derived reviews, short public categorical audit observations and source
hashes are published here, not full ticket/context/media datasets. Keep this
suite's calibration/reference artifacts out of a contestant's source-upload ZIP.
The public-source correspondence and transcript-redaction caveats remain even
after successful hash/quote checks. No competitor code/dependencies/tests were
installed or executed, and no paid provider calls were made in this study.

For reconstruction details and an October release-day checklist, read
[BUILD_AND_ADAPT.md](BUILD_AND_ADAPT.md). Verify actual October rules and overrides
before reusing historical ranking aids; the same categories do not mean the same
task-specific semantic checker.
