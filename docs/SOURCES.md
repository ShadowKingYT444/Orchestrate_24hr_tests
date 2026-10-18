# Orchestrate harness research

Verified 2026-10-18. This is an evidence-based local readiness suite, not a reproduction of the proprietary judge. No hidden answers were accessed. No October task-specific schema is yet established.

## Current official rules

https://help.hackerrank.com/articles/3728112689-hackerrank-orchestrate

General weights code/output/interview/transcript = 30/30/30/10, all categories scored 0–100. Edition instructions can override. Three uploads, each up to 50 MB: code ZIP with README, prescribed output, coding-tool transcript. Exclude supplied datasets, build artifacts and virtual environments. Use environment variables for secrets. Work individually and submit own work. October begins Oct24 12:30 UTC. No public generic CPU, memory, container, network, or runtime limits found. Preparation/reuse permissions are not explicit enough to promise prebuilt solutions are permitted.

## Published historical rubric

https://www.hackerrank.com/blog/behind-the-scenes-of-hackerrank-orchestrate/

May code subweights: architecture30, prompt/tool craft30, robustness25, engineering rigor15. Transcript: direction/ownership35, technical specificity25, iteration/verification25, safety/edge cases15. Reward actual implementation rather than README claims. May output combined per-ticket accuracy with adversarial safety; empty/generic/contradictory justification could cap a ticket around70. Exact judge prompt/model, golden answers, and full output aggregation are not published. May's agent-loop preference should not become a universal requirement: August explicitly permits rules/classifiers/hybrids.

## Historical edition sources

- May support triage: https://github.com/interviewstreet/hackerrank-orchestrate-may26
- June multimodal claims: https://github.com/interviewstreet/hackerrank-orchestrate-june26
- August notification routing: https://github.com/interviewstreet/hackerrank-orchestrate-august26
- September affordability: https://github.com/interviewstreet/hackerrank-orchestrate-september26

June README requires at least two strategy/prompt/model configurations compared, sample metrics, chosen final approach, cost/runtime/token/image/RPM/TPM analysis. Transcript is development-tool conversation, not runtime logs. Multiple development tools' logs should be labeled and combined. September requires final-full-run evaluation/usage_report.md. Logging locations differ: June/August home-directory logs, September repo-root log.txt.

## Exact June structural profile

Source: https://raw.githubusercontent.com/interviewstreet/hackerrank-orchestrate-june26/main/problem_statement.md

Ordered columns: user_id,image_paths,user_claim,claim_object,evidence_standard_met,evidence_standard_met_reason,risk_flags,issue_type,object_part,claim_status,claim_status_justification,supporting_image_ids,valid_image,severity.

Preserve first four input fields; one output per input row. Do not assume user_id unique. claim_object={car,laptop,package}; evidence_standard_met and valid_image={true,false}; claim_status={supported,contradicted,not_enough_information}; severity={none,low,medium,high,unknown}.

issue_type={dent,scratch,crack,glass_shatter,broken_part,missing_part,torn_packaging,crushed_packaging,water_damage,stain,none,unknown}.

object_part by car={front_bumper,rear_bumper,door,hood,windshield,side_mirror,headlight,taillight,fender,quarter_panel,body,unknown}; laptop={screen,keyboard,trackpad,hinge,lid,corner,port,base,body,unknown}; package={box,package_corner,package_side,seal,label,contents,item,unknown}.

risk_flags semicolon list from {none,blurry_image,cropped_or_obstructed,low_light_or_glare,wrong_angle,wrong_object,wrong_object_part,damage_not_visible,claim_mismatch,possible_manipulation,non_original_image,text_instruction_present,user_history_risk,manual_review_required}. supporting_image_ids semicolon filename stems from row image_paths, or none. evaluation/evaluation_report.md required.

## Exact September structural profile

Source: https://raw.githubusercontent.com/interviewstreet/hackerrank-orchestrate-september26/main/problem_statement.md

Ordered columns: request_id,amount_safe_to_pay,affordability_status,recommended_payment_method,payment_plan,earliest_date_for_full_payment,spending_changes_needed,decision_explanation.

Unique input request_id coverage. amount_safe_to_pay finite numeric 0<=x<=requested_amount. affordability_status={affordable_now,affordable_with_plan,affordable_later,not_affordable}; recommended_payment_method={full_payment,partial_payment,installments,wait,not_recommended}. Dates YYYY-MM-DD; earliest_date can be blank; affordable_now requires request_date. payment_plan=none or chronological YYYY-MM-DD:amount entries separated |. Partial requires affordable_with_plan, 0<safe<requested, two payments: safe on request_date, requested-safe on earliest_date; earliest<=desired_completion_date; partial allowed and user-method consent. Installments match supplied option including fees. spending_changes=none or max3 pipe-separated stop:event_id / reduce_to:event_id:new_amount; only flexible recurring expenses; no stop/reduce same event. affordable_with_plan can include full_payment after spending changes. Requires evaluation/usage_report.md tied to final full run: provider/model/calls/tokens/costs. Structural validation cannot prove cashflow safety or hidden correctness.

## Public winners and example repositories

May official leaderboard verifies Saai Syvendra first76.0, Bhavya Khatri second75.7, Faraaz Khan third. Extracted podium scores were placeholder0.0; use table rows. https://www.hackerrank.com/contests/hackerrank-orchestrate-may26/challenges/support-agent/leaderboard

Saai's public repo: https://github.com/saai-syvendra/hackerrank-orchestrate ; writeup https://saai.syvendra.com/myspace/hackerrank-orchestrate . Documents one read-only search/read/grep tool, hybrid retrieval, early injection checks, citations limited to actually read documents. Documentation inspected; no full executable audit.

Official October page reproduces August Mrinal Desai winner84.2 and Muhammad Rifqi Haikal third83.0 testimonials: https://www.hackerrank.com/hackerrank-orchestrate-october26 . No reliably identified public Mrinal repository found.

Swayam June participant repo self-reports third, code27.6/30, transcript9.8/10, output11.4/30. Public version explicitly cleaned up: https://github.com/swayam-mishra/hackerrank-orchestrate/blob/main/hackerrank-orchestrate-june/README.md . Useful documented checks: cached perception vs deterministic replay, image removal/swaps, per-field/per-class metrics, repeated-run variation and operations logs. Direct June leaderboard access failed, so distinguish self-report from independently verified ranking.

GodVilan August first-person postmortem claims exact submitted version plus errata, rank70: https://github.com/GodVilan/Hackerrank-Orchestrate-aug26/blob/main/README.md . Useful caution: strong code/transcript scores do not guarantee strong output score.

## Proposed local dimensions (recommendations, not official scoring)

Artifact safety/size/exclusions; schema/coverage/types/enums; grounding/provenance; sample per-field accuracy and confusion matrices; adversarial robustness; missing-data/model-error/retry handling; reproducibility separating cache replay from fresh runs; evidence-based code review; authentic transcript turn citations; measured usage and cost provenance. Keep deterministic checks, qualitative reviews and unknowns separate. Do not award implementation credit from keywords alone, fabricate transcripts, or treat participant outputs as gold labels.

Report code/output/transcript independently; optionally weighted subtotal out of70. Any normalized100 score must be labeled local only. Do not silently score omitted interview zero, or claim to predict official final scores. Use source/version references per edition; October remains configurable until instructions arrive.
