"""Replay frozen public-review arithmetic, not a model call or candidate rerun."""
import json
import hashlib
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from orchestrate_eval.calibration import calibration_report
from orchestrate_eval.calibration_audit import verify_audit

with tempfile.TemporaryDirectory(prefix='orchestrate-calibration-replay-') as folder:
    result = calibration_report(ROOT/'calibration/dataset-v1.json', folder)
    expected = json.loads((ROOT/'calibration/results-v1.json').read_text())
    if result != expected:
        raise SystemExit('Frozen calibration result differs from verified review arithmetic')
    audit = json.loads((ROOT/'calibration/label-audit-results-v1.json').read_text())
    predictions = ROOT/'calibration/reviews/august-sample-predictions-v1.json'
    metrics = verify_audit(audit, predictions)
    provenance = json.loads((ROOT/'calibration/label-audit-provenance-v1.json').read_text())
    if provenance['raw_prediction_sha256'] != hashlib.sha256(predictions.read_bytes()).hexdigest() or provenance['label_free_input_pack_sha256'] != audit['input_pack_sha256'] or provenance['protocol_sha256'] != audit['protocol_sha256']:
        raise SystemExit('Frozen audit provenance differs from the reviewed prediction/input/protocol identities')
    print(json.dumps({'calibration_replay':'pass', 'numeric_fit_applied':False,
                      'sample_decision_audit':metrics,
                      'warning':'Output official-score calibration remains unresolved; no candidate/model was executed.'}))
