"""Synthetic exact-label audit fixtures. No model/provider calls."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orchestrate_eval.calibration import identity
from orchestrate_eval.calibration_audit import audit_labels, verify_audit


class LabelAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.labels=self.root/'labels.csv'
        self.labels.write_text('message_id,action,message_type\na,notify,direct\nb,mute,promo\nc,digest,group\n')
        self.pack=self.root/'pack.json';self.pack.write_text('{"inputs":"AUTHORED LABEL-FREE UNIT FIXTURE"}')
        protocol={'schema_version':1,'protocol_version':'official-labelled-sample-audit-v1',
                  'sample_size':3,'sample_csv_sha256':hashlib.sha256(self.labels.read_bytes()).hexdigest(),
                  'limits':['Synthetic arithmetic test only.']}
        protocol['protocol_sha256']=identity(protocol,'protocol_sha256')
        self.protocol=self.root/'protocol.json';self.protocol.write_text(json.dumps(protocol))
        self.prediction={'protocol_sha256':protocol['protocol_sha256'],
                         'input_pack_sha256':hashlib.sha256(self.pack.read_bytes()).hexdigest(),
                         'predictions':[{'message_id':'b','action':'notify','message_type':'promo'},
                                        {'message_id':'a','action':'notify','message_type':'direct'},
                                        {'message_id':'c','review_status':'unknown','unknown_reason':'Audio not interpreted.'}]}
        self.predictions=self.root/'predictions.json';self.predictions.write_text(json.dumps(self.prediction))

    def test_ids_not_positions_and_unknowns_not_zero(self):
        report=audit_labels(self.labels,self.predictions,self.protocol,self.root/'report',self.pack)
        self.assertEqual(report['metrics']['reviewed_cases'],2)
        self.assertEqual(report['metrics']['fields']['action']['accuracy_on_reviewed'],.5)
        self.assertEqual(report['metrics']['fields']['message_type']['accuracy_on_reviewed'],1)
        self.assertEqual(report['metrics']['fields']['joint']['accuracy_on_reviewed'],.5)
        self.assertEqual(report['metrics']['fields']['action']['all_case_accuracy_interval'],[1/3,2/3])
        self.assertTrue(report['input_pack_hash_verified'])
        self.assertEqual(verify_audit(report,self.predictions),report['metrics'])

    def test_snapshot_mismatch_and_missing_case_refused(self):
        self.pack.write_text('changed')
        with self.assertRaises(ValueError):audit_labels(self.labels,self.predictions,self.protocol,self.root/'report',self.pack)
        self.labels.write_text(self.labels.read_text().replace('mute','notify'))
        with self.assertRaises(ValueError):audit_labels(self.labels,self.predictions,self.protocol,self.root/'report')

    def test_replay_recomputes_not_trusting_saved_flags_or_aggregates(self):
        report=audit_labels(self.labels,self.predictions,self.protocol,self.root/'report')
        changed=copy.deepcopy(report);changed['metrics']['fields']['action']['correct']=2
        changed['report_sha256']=identity(changed,'report_sha256')
        with self.assertRaises(ValueError):verify_audit(changed,self.predictions)
        changed=copy.deepcopy(report);changed['rows'][0]['predicted']['action']='mute'
        changed['report_sha256']=identity(changed,'report_sha256')
        with self.assertRaises(ValueError):verify_audit(changed,self.predictions)
        for field in ('protocol_sha256','input_pack_sha256'):
            changed=copy.deepcopy(report);changed[field]='a'*64
            changed['report_sha256']=identity(changed,'report_sha256')
            with self.assertRaises(ValueError):verify_audit(changed,self.predictions)
        changed=copy.deepcopy(report);changed['rows'][0]['action_correct']=False
        changed['report_sha256']=identity(changed,'report_sha256')
        with self.assertRaises(ValueError):verify_audit(changed,self.predictions)

    def test_raw_predictions_are_frozen_and_previous_results_preserved(self):
        report=audit_labels(self.labels,self.predictions,self.protocol,self.root/'report')
        self.assertEqual((self.root/'report/predictions-frozen.json').read_bytes(),self.predictions.read_bytes())
        self.prediction['predictions'][0]['action']='mute'
        self.predictions.write_text(json.dumps(self.prediction))
        with self.assertRaises(ValueError):verify_audit(report,self.predictions)
        with self.assertRaises(ValueError):audit_labels(self.labels,self.predictions,self.protocol,self.root/'report')


if __name__=='__main__':
    unittest.main()
