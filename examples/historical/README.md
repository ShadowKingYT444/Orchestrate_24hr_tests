# Synthetic historical schema examples

These tiny fixtures were written for this evaluator. They are **not official
challenge datasets**, expected-answer datasets, or evidence of competition
performance. Image paths are placeholders; there are no associated images.
June deliberately repeats the same input row to demonstrate preserved duplicate
claims. September demonstrates a structurally valid two-payment plan only.

Run from the repository root; both `input_csv` in the task JSON and the output
path resolve relative to the **current working directory**, not the task file.

```python
from orchestrate_eval.historical import evaluate_historical
import json
from pathlib import Path

month = 'june'  # or 'september'
root = Path('examples/historical')
task = json.loads((root / f'{month}-task.json').read_text())
print(evaluate_historical(root / f'{month}-output.csv', task))
```

CSV inputs and outputs are limited to 5,000,000 bytes each. Symlinks, invalid
UTF-8, malformed row widths, duplicate column names, and incorrect ordered
output columns fail. June's first four fields must match input row by row.
September requires nonempty, unique request IDs with exact input coverage.

A valid fixture still has `unknown` checks. Schema validation does not decide
whether a photographed claim is correct, whether evidence is sufficient, or
whether an actual person can safely afford a payment. September does not check
consent, installment-option eligibility, 90-day forecast semantics, spending
change semantics, or the financial calculations themselves. Those need the
complete auxiliary datasets and an independently validated evaluator. June
unrecognized image-reference delimiters are reported as unknown rather than
being guessed.

Reference specifications:

- https://raw.githubusercontent.com/interviewstreet/hackerrank-orchestrate-june26/main/problem_statement.md
- https://raw.githubusercontent.com/interviewstreet/hackerrank-orchestrate-september26/main/problem_statement.md
