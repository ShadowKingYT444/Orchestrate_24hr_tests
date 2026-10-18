"""Replay preserved actual runs and independent model reviews, without API calls.
For fresh agent execution, use benchmark run instead. Runtime traces are not coding transcripts.
"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from orchestrate_eval.cli import main
root=Path(__file__).resolve().parents[1]
for kind in ('strong','weak'):
    code=main(['benchmark','judge-import','--bundle',str(root/f'benchmarks/results/{kind}-bundle.json'),
          '--review',str(root/f'benchmarks/results/{kind}-review.json'),
          '--benchmark-report',str(root/f'benchmarks/results/{kind}-run.json'),
          '--report-dir',str(root/f'reports/demo-{kind}')])
    if code:raise SystemExit(code)
raise SystemExit(main(['benchmark','compare',str(root/'reports/demo-strong/benchmark.json'),str(root/'reports/demo-weak/benchmark.json'),
      '--report-dir',str(root/'reports/demo-comparison')]))
