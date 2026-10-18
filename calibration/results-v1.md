# Frozen calibration comparison

Observed differences between assessments. Not matched-upload prediction errors, a truly blind holdout, statistical calibration, or cross-edition ranking validation.

| Case | Category | Official | Original local | After frozen protocol | Original absolute gap | After absolute gap |
|---|---|---:|---:|---:|---:|---:|
| saai-may-development | code /30 | 26.4 | 17.8125 | 23.1000 | 8.5875 | 3.3000 |
| saai-may-development | output /30 | 22.8 | 26.0819 (unchanged) | 26.0819 (unchanged) | 3.2819 | 3.2819 |
| saai-may-development | coding_transcript /10 | 8.2 | Unknown / not reviewed | Unknown / not reviewed | Not calculable | Not calculable |
| godvilan-august-external | code /30 | 22.8 | Unknown / not reviewed | 24.1500 | Not calculable | 1.3500 |
| godvilan-august-external | output /30 | 13.8 | Unknown / not reviewed | Unknown; contribution interval 22.4080–24.5898 | Not calculable | 8.6080–10.7898 (interval) |
| godvilan-august-external | coding_transcript /10 | 9.8 | Unknown / not reviewed | 8.8000 | Not calculable | 1.0000 |
| swayam-june-context | code /30 | 27.6 | Unknown / not reviewed | Unknown / not reviewed | Not calculable | Not calculable |
| swayam-june-context | output /30 | 11.4 | Unknown / not reviewed | Unknown / not reviewed | Not calculable | Not calculable |
| swayam-june-context | coding_transcript /10 | 9.8 | Unknown / not reviewed | Unknown / not reviewed | Not calculable | Not calculable |

Unknown is not zero. Intervals cover missing row contributions only, not statistical uncertainty or expected official-score coverage.

No offset, rescaling or target-aware score fitting is applied.

## Evidence and interpretation limits

- saai-may-development: Public source/output linked to the winner, stable since May1 code/output commit; original server-upload hashes not available. No genuine public coding transcript.
- godvilan-august-external: Participant claims unchanged graded source/output/log; caches/data omitted. Posted log and later README disagree about ASR-cache ZIP inclusion; server archive equivalence unresolved. Log contains redactions/action summaries, not proven raw complete transcript.
- swayam-june-context: Explicitly cleaned-up public source with made-up demonstration data; graded output and original coding transcript absent. Not a matched calibration case.
- Official scores and entrant identities were known before this study; review inputs omit explicit targets but this is not truly blind.
- Public source/output/logs are not byte-authenticated server submissions.
- Two selected entrants across different tasks/editions cannot establish statistical calibration or ranking accuracy.
- No numeric offset/rescaling is fitted. Opposite category gaps can cancel; do not treat a nearly matching subtotal as calibration success.
- Unknown categories and unreviewed media are not zero. Partial-output intervals cover missing contributions only, not judgment uncertainty.
- No downloaded candidate code/dependencies/tests were executed; no paid provider calls were made.
