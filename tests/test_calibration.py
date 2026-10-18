"""Synthetic arithmetic/evidence fixtures, not official model-judge grades."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from orchestrate_eval.calibration import (load_protocol, export_calibration_bundle,
    freeze_review, validate_frozen, output_estimate, calibration_report)

ROOT = Path(__file__).resolve().parents[1]


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'agent.py').write_text('def answer():\n    return "reference"\n')
        self.protocol = self.root / 'protocol.json'
        self.protocol.write_text((ROOT / 'calibration/protocol-v1.json').read_text())
        self.bundle_path = self.root / 'bundle.json'
        self.bundle = export_calibration_bundle(self.source, self.bundle_path, self.protocol, 'may26')
        entry = {'score':75,'rationale':'Synthetic review of the concrete test function, not a real agent grade.',
                 'evidence':[{'source':'code/agent.py','start_line':1,'end_line':2,'quote':'return "reference"'}]}
        self.review = {'schema_version':1,'origin':'human','reviewer':'SYNTHETIC UNIT FIXTURE',
                       'bundle_id':self.bundle['bundle_id'],
                       'calibration_protocol_sha256':self.bundle['calibration_protocol']['protocol_sha256'],
                       'categories':{'code':{name:copy.deepcopy(entry) for name in self.bundle['rubrics']['code']},
                                     'coding_transcript':None,'output':None}}
        self.review_path = self.root / 'review.json'
        self.review_path.write_text(json.dumps(self.review))

    def test_protocol_and_edition_are_explicit(self):
        protocol = load_protocol(self.protocol)
        self.assertEqual(protocol['category_weights']['coding_transcript'],10)
        self.assertNotIn('official_points',self.bundle)
        with self.assertRaises(ValueError):
            export_calibration_bundle(self.source,self.root/'unknown.json',self.protocol,'october')
        with self.assertRaises(ValueError):
            export_calibration_bundle(self.source,self.bundle_path,self.protocol,'may26')
        protocol['category_weights']['code']=99
        self.protocol.write_text(json.dumps(protocol))
        with self.assertRaises(ValueError):load_protocol(self.protocol)

    def test_committed_study_arithmetic_replays_without_models(self):
        result=calibration_report(ROOT/'calibration/dataset-v1.json',self.root/'replay')
        self.assertEqual(result,json.loads((ROOT/'calibration/results-v1.json').read_text()))
        rows=result['rows']
        saai=next(row for row in rows if row['case_id']=='saai-may-development' and row['category']=='code')
        self.assertEqual(saai['before']['points'],17.8125)
        self.assertEqual(saai['after']['points'],23.1)
        external=next(row for row in rows if row['case_id']=='godvilan-august-external' and row['category']=='output')
        self.assertIsNone(external['after']['points'])
        self.assertGreater(external['after']['whole_output_interval'][0],external['official_points'])

    def test_freeze_reverify_and_preserve_originals(self):
        destination=self.root/'frozen.json'
        artifact=freeze_review(self.bundle_path,self.review_path,destination)
        self.assertEqual(validate_frozen(artifact,self.bundle)['code'],75)
        with self.assertRaises(ValueError):freeze_review(self.bundle_path,self.review_path,destination)
        changed=copy.deepcopy(artifact);changed['category_scores_100']['code']=100
        with self.assertRaises(ValueError):validate_frozen(changed)
        changed=copy.deepcopy(self.bundle);changed['untrusted_evidence_files'][0]['text']='forged'
        with self.assertRaises(ValueError):validate_frozen(artifact,changed)

    def test_new_ratings_bind_protocol_and_predeclared_steps(self):
        for mutate in ('protocol','step'):
            review=copy.deepcopy(self.review)
            if mutate=='protocol':review['calibration_protocol_sha256']='wrong'
            else:review['categories']['code']['architecture']['score']=77
            self.review_path.write_text(json.dumps(review))
            with self.assertRaises(ValueError):
                freeze_review(self.bundle_path,self.review_path,self.root/(mutate+'.json'))

    def partial_output(self):
        keys=('action','message_type','reason','evidence_relevance','confidence_reasonableness')
        def row(identifier,rating):
            return {'message_id':identifier,'ratings_0_to_4':dict.fromkeys(keys,rating),
                    'flags':dict.fromkeys(('unsafe_notify','contradicted_or_invented_reasoning','irrelevant_or_generic_reason'),False),
                    'rationale':'Synthetic context-grounded fixture judgment for arithmetic only.',
                    'evidence_refs':[{'source_file':'context.csv','record_key':'authored-row','sha256':'a'*64}]}
        return {'review_kind':'august_partial_grounded','total_case_count':3,
                'source_hashes':{'context.csv':'a'*64},
                'local_field_weights':dict(zip(keys,(35,20,25,15,5))),
                'case_reviews':[row('a',4),row('b',0),{'message_id':'c','review_status':'unknown',
                    'ratings_0_to_4':None,'unknown_reason':'Audio was not interpreted.'}]}

    def test_unknown_rows_are_not_zero_filled_point_estimates(self):
        result=output_estimate(self.partial_output(),30)
        self.assertIsNone(result['points'])
        self.assertEqual(result['reviewed_mean_points'],15)
        self.assertEqual(result['whole_output_interval'],[10,20])
        self.assertEqual(result['unknown_cases'],1)

    def test_semantic_caps_apply_to_the_whole_reviewed_case(self):
        for flag,expected in [('unsafe_notify',7.5),('contradicted_or_invented_reasoning',15),('irrelevant_or_generic_reason',21)]:
            review=self.partial_output();review['case_reviews']=review['case_reviews'][:1];review['total_case_count']=1
            review['case_reviews'][0]['flags'][flag]=True
            self.assertEqual(output_estimate(review,30)['points'],expected)
        review=self.partial_output();review['case_reviews'][0]['ratings_0_to_4']['action']=float('nan')
        with self.assertRaises(ValueError):output_estimate(review,30)

    def test_context_references_are_hash_bound_not_arbitrary_text(self):
        for reference in (None,'claim',{'source_file':'context.csv','record_key':'row','sha256':'b'*64}):
            review=self.partial_output();review['case_reviews'][0]['evidence_refs']=[reference]
            with self.assertRaises(ValueError):output_estimate(review,30)

    def test_malformed_semantic_flags_fail_cleanly(self):
        for flags in (None, []):
            review=self.partial_output();review['case_reviews'][0]['flags']=flags
            with self.assertRaises(ValueError):output_estimate(review,30)

    def test_method_profile_and_huge_ratings_fail_closed(self):
        protocol=json.loads((ROOT/'calibration/protocol-v1-august-output.json').read_text())
        protocol['output_protocol']['august_routing_saved_answers']['caps_local']['unsafe_notify']=10
        from orchestrate_eval.calibration import identity
        protocol['protocol_sha256']=identity(protocol,'protocol_sha256')
        self.protocol.write_text(json.dumps(protocol))
        with self.assertRaisesRegex(ValueError,'weights/caps/scale'):load_protocol(self.protocol)
        base=json.loads((ROOT/'calibration/protocol-v1.json').read_text())
        review=self.partial_output();review['protocol_sha256']=base['protocol_sha256']
        with self.assertRaisesRegex(ValueError,'method-bearing amendment'):output_estimate(review,30,base)
        review=self.partial_output();review['case_reviews'][0]['ratings_0_to_4']['action']=10**400
        with self.assertRaises(ValueError):output_estimate(review,30)
        review=self.partial_output();review['case_reviews'][0]['ratings_0_to_4']['action']=2.5
        with self.assertRaisesRegex(ValueError,'integer0..4'):output_estimate(review,30)

    def test_dataset_recomputes_gaps_and_refuses_changed_review_or_escape(self):
        artifact=freeze_review(self.bundle_path,self.review_path,self.root/'frozen.json')
        sha=hashlib.sha256((self.root/'frozen.json').read_bytes()).hexdigest()
        reference={'kind':'frozen_rubric_review','path':'frozen.json','sha256':sha}
        dataset={'schema_version':1,'study':'SYNTHETIC UNIT FIXTURE','targets_known_before_protocol':True,
                 'protocols':[{'path':'protocol.json','protocol_sha256':artifact['protocol_sha256']}],
                 'cases':[{'id':'synthetic-a','role':'development','edition':'may26',
                           'official_points':{'code':24,'output':None,'coding_transcript':None},
                           'official_source_url':'https://example.invalid/synthetic',
                           'before':{},'after':{'code':reference}}]}
        path=self.root/'dataset.json';path.write_text(json.dumps(dataset))
        report=calibration_report(path,self.root/'report')
        self.assertEqual(report['rows'][0]['after']['signed_gap'],-1.5)
        self.assertIsNone(report['rows'][2]['after'])
        self.assertFalse(report['numeric_fit_applied'])
        dataset['cases'][0]['after']['code']['path']='../outside.json'
        path.write_text(json.dumps(dataset))
        with self.assertRaises(ValueError):calibration_report(path,self.root/'report')
        dataset['cases'][0]['after']['code']['path']='frozen.json'
        path.write_text(json.dumps(dataset));(self.root/'frozen.json').write_text('{}')
        with self.assertRaises(ValueError):calibration_report(path,self.root/'report')


if __name__=='__main__':
    unittest.main()
