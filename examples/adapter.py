"""Deterministic local harness adapter: synthetic data only, no APIs or network."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--output", required=True)
args = parser.parse_args()
Path(args.output).write_text(json.dumps({"answers": {"sum": sum([3, 4]), "sorted": sorted([3, 1, 2]), "empty": []}}), encoding="utf-8")
