# Genuine coding agents: integration and verified limits

There are two different roles. A **developer agent** such as Codex edits the
submitted support agent and creates genuine development evidence. A **task agent**
handles support tickets through search/read tools. Running a rule-based task agent
does not test Codex. A native model reviewing saved evidence does not test Codex.

## Actual local result, 2026-10-18

The real installed `codex-cli 0.159.2` was inspected. `codex login status` confirmed
an existing ChatGPT login; no stored API-key route was used. The read-only quota
RPC could not start because its state directory is read-only, so remaining quota
is unknown. There was one bounded integrated developer attempt, not a batch.

Command shape:

```sh
python -m orchestrate_eval coding-agent run --allow-exec --allow-model-turn --model gpt-6.1 --timeout 120 --report-dir reports/codex-repair
```

The adapter actually invoked `codex exec --json --ephemeral --sandbox
workspace-write --color never --model gpt-6.1 -c
'model_reasoning_effort="xhigh"' -C DISPOSABLE_WORKSPACE -`, with the repair prompt
on stdin. It exited **1 after 4.33 seconds**, before any JSONL/model events:

```text
Error: failed to initialize in-process app-server client: Read-only file system (os error 30)
```

No model turn completed, no agent source changed, and **no Codex performance,
coding-transcript or contest score is claimed**. The requested model was not
confirmed by a completed response. The selected evidence summary is in
[codex-live-smoke.json](validation/codex-live-smoke.json). No credentials were
copied, no new login/grant was created, and filesystem policy was not loosened.
The startup error must be resolved in a normally writable, authorized Codex
installation before live integration can be validated. The suite does not try to
work around this environment's restriction.

## What the runnable adapter does

```sh
python -m orchestrate_eval coding-agent inspect
python -m orchestrate_eval coding-agent run --allow-exec --allow-model-turn --model YOUR_AVAILABLE_MODEL --timeout 120 --report-dir reports/codex-repair
```

It requires an existing ChatGPT login and refuses automatic API-key fallback. It
creates a fresh Git task directory containing an authored support-agent scaffold
with two documented regressions: authorization handoff and retrieved invoice
currency. The developer receives the protocol and repair request, with no gold
casepack or evaluator code in its workspace. The host preserves the original CLI
JSONL, stderr, exact user prompt, source hashes and patch. It never silently
overwrites prior evidence.

After a successful real model turn, the host executes the produced adapter on all
12 held-out support cases at a recorded seed. The actual search/read runtime
traces are separate from the genuine Codex development events. The pipeline then
exports produced source + coding evidence + runtime references in one judge
bundle. Follow the normal `benchmark judge-import` workflow to judge every answer
and the code/transcript rubrics. Machine facts alone do not yield a complete
quality score. Mocked tests verify this wiring; they are not model completions.

Both execution and model-turn flags are required. There is one attempt per
invocation, a maximum 180-second deadline, bounded logs, and no retry/batch. API
keys are not inherited. Native CLI auth is used in place through its existing
home; credentials are never copied. Costs/tokens remain unknown unless reported.
If remaining usage is known, pass `--remaining-usage-percent N`; values at or below
10% are refused. With unknown quota this small smoke cannot guarantee a reserve
or a billing cap. Do not expand it into a broad batch without checking allowance.

The Codex workspace-write request and disposable directory are not an independent
VM/container or proof against all filesystem access. Only run trusted agents and
inspect source before using an untrusted integration. Production isolation and
credential/network/resource controls remain the operator's responsibility.

## Coverage and gaps

This specific scaffold repair would test coding integration, two bug fixes,
observed verification and the produced task agent's held-out behavior. It is not
from-scratch architecture development, long-horizon agent engineering or a
comprehensive contest benchmark. The live attempt did not reach even that scope.

The local support world covers five policies, multilingual prompts, authorization,
unsupported requests, injection and simulated tool-error envelopes. It lacks
official hidden gold, broad real-world tasks, arbitrary external tools, real
damaged-JSON transport, multimodal inputs, official safety aggregation, repeated
live model runs, hard OS containment and statistically validated rank prediction.
The [official-score comparison](OFFICIAL_SCORE_COMPARISON.md) shows material
local-versus-official gaps. Treat scores as development diagnostics until a
multi-entrant held-out calibration supports a stronger claim.
