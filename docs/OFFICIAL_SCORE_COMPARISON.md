# Official-score comparison and calibration audit, version 1

Verified 2026-10-18. This report preserves the original local estimates. No score has been adjusted after seeing the official breakdown.

## Result

The original local estimates are not a calibrated reproduction of the official grades. For Saai Syvendra, HackerRank publishes **code 26.4/30 and output 22.8/30**; the existing local public-artifact reviews gave **17.8125/30 and 26.0819/30**. The observed absolute gaps are **8.5875 code points and 3.2819 output points**. These are numerical differences between two assessments, not proven matched-artifact prediction errors: the public files have not been cryptographically matched to the server-submitted files.

## Saai: directly observed official results versus original local judgments

All values below are already weighted final-score points. The official payload and visible headers establish category maxima; no split was inferred from the total.

| Category | Official contest result | Original local result | Local minus official | Absolute observed gap | Comparison qualification |
|---|---:|---:|---:|---:|---|
| Code ZIP | 26.4 / 30 | 17.8125 / 30 | -8.5875 | 8.5875 | Same named category; public source snapshot rather than verified submitted ZIP |
| Output CSV | 22.8 / 30 | 26.08189655 / 30 | +3.28189655 | 3.28189655 | Same named category and public 29-ticket bank; different scoring method and unverified submitted-output identity |
| Coding transcript | 8.2 / 10 | Unknown | Not calculable | Not calculable | No authentic public coding export was available locally |
| AI interview | 18.6 / 30 | Excluded | Not applicable | Not applicable | Outside the requested local non-voice scope |
| Code + output | 49.2 / 60 | 43.89439655 / 60 | -5.30560345 | 5.30560345 | Descriptive subtotal gap; cancellation of opposite category errors is not calibration success |
| Non-voice subtotal | 57.4 / 70 | Unknown; missing-transcript interval 43.8944–53.8944 / 70 | Not calculable as a complete local prediction | Not calculable | Local interval describes only absent-category points, not statistical uncertainty or expected official-score coverage |
| Final overall score | 76.0 / 100 | No complete overall prediction | Not calculable | Not calculable | Do not compare an incomplete /60 local subtotal against official /100 |

For additional scale clarity: official code is 88/100 and output 76/100 before category weighting; local code is 59.375/100 and output about 86.9397/100. Official transcript is 82/100 and interview 62/100. Only the published precision is established.

### Primary official evidence

- [Official May leaderboard](https://www.hackerrank.com/contests/hackerrank-orchestrate-may26/challenges/support-agent/leaderboard): rank 1, Saai Syvendra, username `saaisyvendras`. The actual table row and Next.js payload agree: `code_zip=26.4`, `output_csv=22.8`, `chat_transcript=8.2`, `interview=18.6`, `score=76`.
- Embedded data path: `__NEXT_DATA__.props.pageProps.dehydrateState.queries[2].state.data`; winner is `entries[0]`, repeated in `top_three[0]`. Stage maxima are in `evaluation.stages`; total maximum is 100. The result is marked final and all stages released.
- [Current official guide](https://help.hackerrank.com/articles/3728112689-hackerrank-orchestrate): four independent 0–100 signals weighted code/output/interview/transcript 30/30/30/10, with edition-specific overrides possible.
- [Official May methodology](https://www.hackerrank.com/blog/behind-the-scenes-of-hackerrank-orchestrate/): published rubric dimensions and output methodology.
- Preserved selected evidence: [selected official payload](validation/may26-official-leaderboard.json). The source HTML digest is recorded below; a full third-party HTML copy is not redistributed. HTML SHA-256: `8d365766aa089ece2ff06e611b74297767db65f4ae76e04878e85a19ade5022f`.
- Rendering caution: animated podium cards contain 0.0 placeholders. The table and hydrated score objects, not those placeholders, establish the results.

## Artifact identity and version comparison

The local reviews used [Saai's public snapshot](https://github.com/saai-syvendra/hackerrank-orchestrate/tree/fadb4f24e36d860a9ce4d5155bb30568df80ea4b), commit `fadb4f24e36d860a9ce4d5155bb30568df80ea4b` dated May 25.

GitHub's [pinned comparison](https://github.com/saai-syvendra/hackerrank-orchestrate/compare/0e06300ce6faaae3997a951dcf6018de201c2967...fadb4f24e36d860a9ce4d5155bb30568df80ea4b) establishes exactly one changed file: root README.md. Code, supplied corpus, input and saved output are unchanged from the parent [May 1 commit](https://github.com/saai-syvendra/hackerrank-orchestrate/commit/0e06300ce6faaae3997a951dcf6018de201c2967). That parent was authored/committed at `2026-05-01T12:40:30Z` and its message says the output was regenerated after routing/prompt changes. Thus this is stronger than an untraceable cleaned-up reimplementation; it is still not proof of which ZIP/CSV the contest server received. Commit timestamps and participant claims are not upload attestations.

- Saved CSV SHA-256: `42ee580ca5e8b9a5caa819be7d86ee026646e9035e8e82b656eaedda64d4b0fd`.
- Input SHA-256: `7c862a89c5353d167a8c856aedfd12a4c799fc8bcc3b1acaabfc899c70be22e3`.
- Local scope: all 27 Python source files statically read, all 29 saved answers qualitatively reviewed against the supplied primary corpus. No candidate module import, test execution, installation or paid agent rerun was performed.
- No server-upload ZIP/CSV hash, original server judge report, original authentic development transcript, or per-ticket official judgments was accessible in the reviewed public material.
- The public 10-row labelled sample has zero input-key overlap with the 29 prediction rows. It cannot supply exact gold labels for these saved predictions. The existing candidate sample-evaluation script compares by position, so its numbers would not remedy that mismatch.

The [participant's May 25 write-up](https://saai.syvendra.com/myspace/hackerrank-orchestrate) corroborates the agent design, 29-ticket scope and winning identity, but does not publish the category breakdown or prove a byte-identical contest upload.

## Why the local/official difference is a calibration failure, not an arithmetic bug

1. **Code-rubric emphasis drift.** The official engineering-rigor criterion has 15% weight and names modularity, type hints, environment-based secrets and function size. The local criterion was labelled experimental rigor and gave substantial emphasis to tests, lockfiles, CI and sample-evaluation weaknesses. Those are useful engineering-audit findings, but they are not the same published emphasis. Preserve the audit findings separately from a rubric-faithful prediction.
2. **Unpublished scoring anchors.** The four dimension weights match the May aid, but local 0/25/50/75/100 anchors and the severity of deductions were locally chosen. Source-derived defects need not receive the same penalty from the proprietary model. Official per-dimension scores are not public, so the 8.5875-point gap cannot be attributed to one dimension.
3. **Rigor alone cannot explain the gap.** Raising only the original rigor rating from 37.5/100 to the theoretical maximum 100/100 would add 2.8125 points out of 30, still leaving 5.775 code points below the official grade. Do not claim that a single rubric-label correction solves calibration.
4. **Different output method.** The local output review used explicit local field weights 25/10/10/35/20, ordinal qualitative ratings, supplied KB evidence and a local justification cap. HackerRank describes per-ticket judgment against its private golden dataset plus a submission-level adversarial safety score. The full aggregation is unpublished. The local review is useful answer-quality criticism, but it was never exact-gold accuracy.
5. **Unknown causal attribution.** The local review found concrete hotline/routing/justification/language problems. The official aggregate does not show whether or how those exact issues were penalized. Do not invent an explanation for the official 22.8 from the local findings.
6. **Edition/architecture mismatch in the demonstration grades.** The competent authored demonstration was a deterministic rule program and received a broad local architecture rating of 75/100. The published May architecture aid favors actual model-directed agent/tool loops, whereas later editions allowed rules and hybrids. Its general-engineering review must not be represented as a faithful May architecture prediction. Make edition/rubric version explicit.
7. **One example is not a calibration set.** Preserve these estimates and gaps as an honest diagnostic. Do not scale all future scores to make this winner match, or claim predictive ranking accuracy from this observation.

## Predeclared next calibration protocol (proposal; no new grade assigned here)

Before any regrade, freeze and version the rubric text, anchors, evidence requirements and output aggregation. For a May-rubric-faithful code score, use the published architecture/prompt-tool/robustness/engineering criteria directly; keep extra test/CI/lockfile/operations audits in a separate unweighted section unless the edition explicitly includes them. Preserve the original review alongside any new one and explain every criterion change before producing its new score.

Use multiple independently identifiable submitted artifacts with actual category scores; mark participant screenshots/self-reports separately from official leaderboard values. Blind reviewers to names/rank/results when practical. Tune on a development calibration set, then evaluate signed bias, absolute error and rank ordering on held-out entrants. Do not report those statistics as validation while exact submission identity and sample size remain inadequate. Missing transcripts stay unknown; an official transcript score does not permit fabricating a local transcript review.

## Minimum genuine-agent runtime smoke

The published v0.3 executable demonstrations are real subprocess runs, but their authored agents are deterministic rules; they are not a real Codex-powered agent evaluation. A genuine-agent smoke should establish the following before that claim is made:

1. Use an actually available, user-authorized genuine Codex runtime/model through the adapter, and record exact command/model/runtime version, source snapshot, seed, timestamps, failures and complete actual tool messages. No canned answers, case-ID lookup, precomputed predictions, mocked model success or gold-file reads.
2. Run at least the full 12-case held-out policy-world split at a new seed. It covers factual/counterfactual lookup, authorization, multilingual requests, ticket/corpus injection, unsupported topics and upstream failures. The malformed-upstream case is an explicit error envelope, not damaged JSON transport; test actual malformed transport separately if claiming that coverage.
3. Keep the policy references host-side and verify every citation against a document actually read. Since this harness is not sandboxed, withholding gold from stdin alone does not prevent filesystem access; source review or separately provisioned isolation is needed for stronger evidence.
4. Judge the meaning of every response and justification against the frozen reference and read trace, including contradictory extra clauses, invented policy and unauthorized-action claims. Include every failure; compare to the same-case weak/rule baseline. A single smoke establishes functionality, not stochastic reliability; repeated runs and multiple seeds are the next measurement.
5. Keep agent runtime traces distinct from authentic development-tool coding exports. Only a real supplied development export can support the transcript category. Do not claim a complete /70 merely because the agent runtime was logged.
6. No new paid provider calls or downloaded external-agent execution is authorized by this report. If the selected runtime requires new spending, credentials, installation or other approval, pause that dependent action for the appropriate authorization. Missing costs/tokens remain unknown rather than zero.

## Additional entrants: directly verified official scores and accessible artifacts

These score records were read directly from public, unauthenticated HackerRank JSON endpoints and match pinned participant-posted records. No local quality grades were produced for these additional artifacts in this pass, so there are no legitimate local-versus-official errors to calculate for them yet.

| Entrant / edition | Official code /30 | Official output /30 | Official transcript /10 | Official interview /30 | Official total /100 | Rank | Local comparison status |
|---|---:|---:|---:|---:|---:|---:|---|
| Swayam Mishra / June | 27.6 | 11.4 | 9.8 | 21.3 | 70.1 | 3 | Current public code is explicitly cleaned up; fake demo data replace contest data; original output/transcript absent. Context only, not a matched calibration pair. |
| Srikanth Reddy Nandireddy / GodVilan / August | 22.8 | 13.8 | 9.8 | 26.7 | 73.1 | 70 | Public source, saved 110-row output and build log available; author claims source unchanged from graded submission, but omitted caches/data and log redaction/summaries require caveats. Eligible next exploratory calibration case, not an attested exact upload. |

Primary direct score endpoints:

- [Official June page 1](https://www.hackerrank.com/community/hackathon/leaderboard?contest_id=385706&challenge_id=581108&page=1): Swayam hacker ID 22501438, current username swayammishra. Published historical mirror used swayammishra1504; stable ID, rank, category values and total match.
- [Official August page 3](https://www.hackerrank.com/community/hackathon/leaderboard?contest_id=388008&challenge_id=586433&page=3): Srikanth hacker ID 14097920, username srikanth2402. All four stages released, final result.

The live participant totals are 1,771 June and 1,982 August, while the historical exports/screenshots show 1,773 and 1,983. Do not silently present the old denominators as current; target ranks and scores still agree.

Pinned artifact pointers:

- [Swayam June README](https://github.com/swayam-mishra/hackerrank-orchestrate/blob/fc033c4026cd8b751dd121cf7dbce8925d18e58c/hackerrank-orchestrate-june/README.md): source/data changes and local-dev-metric scope are explicit. Its reported 90–95% sample claim-status accuracy is not equivalent to the official 11.4/30 output score.
- [GodVilan README](https://github.com/GodVilan/Hackerrank-Orchestrate-aug26/blob/3d54cc73874c17482e76a266836f70e7f7aa14fa/README.md): author states source is unchanged and lists omitted transcript/model-response caches. No end-to-end rerun is possible from this checkout alone without the original dataset.
- [GodVilan saved output](https://github.com/GodVilan/Hackerrank-Orchestrate-aug26/blob/3d54cc73874c17482e76a266836f70e7f7aa14fa/results/output.csv): 110 rows/unique message IDs; SHA-256 `01da0311b2342fd7a831df7de7c78745de643632fc3866cd9f7434d869ff5e4a`.
- [GodVilan posted build log](https://github.com/GodVilan/Hackerrank-Orchestrate-aug26/blob/3d54cc73874c17482e76a266836f70e7f7aa14fa/transcript/log.txt): dated development/verification/packaging entries, with redaction and summary language; SHA-256 `aeb6e17b4b3bb967def95b7d011aea014308d7d050df5ec0556ee06b747637c7`. Do not assert raw, unabridged, byte-identical transcript authenticity from public presence alone.
- [GodVilan scorecard image](https://github.com/GodVilan/Hackerrank-Orchestrate-aug26/blob/3d54cc73874c17482e76a266836f70e7f7aa14fa/results/scorecard-august.png): visually confirms the displayed category values, but the cropped image lacks visible username/event/date. Direct official identity-linked JSON provides the stronger score authority.

Full provenance and saved raw official responses are documented in `orchestrate-participant-score-evidence.md` and `orchestrate-participant-evidence/` in this shared directory. These external files were read/parsed only; no downloaded agent code was executed. No raw external code/data/transcript should be vendored into the evaluator without an appropriate license/permission review.

## Versioned implementation response

The original frozen reviews remain `local-audit-v1-preserved`, including their original scores and general engineering criticisms. New exports use `may26-published-aid-v2`: engineering rigor is explicitly modularity, annotations, environment-held secrets and manageable functions. Extra tests/CI/lockfile concerns belong in an optional unweighted audit unless directly relevant to another published criterion. No new Saai grade was assigned after viewing official scores. These changes improve rubric fidelity; they do not establish calibration or reproduce hidden rating anchors.

For the actual Codex integration result, see [CODING_AGENTS.md](CODING_AGENTS.md). The real local CLI startup failed before a model turn; successful mocked wiring tests are kept separate from live validation.
