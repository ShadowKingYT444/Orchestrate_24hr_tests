import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

from orchestrate_eval.benchmark import (apply_semantics, benchmark_identity, execute_case, grade_case,
                                       run_benchmark, scorecard, tool_response, compare_benchmarks)
from orchestrate_eval.benchmark_cases import casepack
from orchestrate_eval.judging import export_bundle, import_review, judge_http

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temporary.name)
        cls.strong = run_benchmark([sys.executable,str(ROOT/'examples/agents/strong.py')],ROOT,cls.root/'strong',split='all',trusted=True)
        cls.weak = run_benchmark([sys.executable,str(ROOT/'examples/agents/weak.py')],ROOT,cls.root/'weak',split='all',trusted=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_actual_tool_runs_and_counterfactuals(self):
        self.assertEqual(self.strong['machine_component_mean_85'],85)
        self.assertLess(self.weak['machine_component_mean_85'],30)
        self.assertIsNone(self.strong['output_score_100'])
        self.assertIsNone(self.strong['exact_case_pass_rate'])
        self.assertEqual(len(self.strong['runs']),20)
        for run in self.strong['runs']:
            incoming=run['trace'][0]['payload']
            self.assertNotIn('expected',incoming['case'])
            self.assertNotIn('facts',incoming['case'])
        self.assertNotEqual(casepack(0)['sha256'],casepack(73)['sha256'])
        pack=casepack(73)
        run=execute_case([sys.executable,str(ROOT/'examples/agents/strong.py')],ROOT,pack,pack['cases'][0],trusted=True)
        self.assertEqual(grade_case(run,pack['cases'][0],pack)['machine_points_85'],85)
        self.assertTrue(run['read_document_ids'])

    def test_committed_native_reviews_replay_with_actual_source_and_scores(self):
        for kind,expected in [('strong',47.9325),('weak',9.75)]:
            folder=ROOT/'benchmarks/results'
            bundle=json.loads((folder/f'{kind}-bundle.json').read_text())
            source=next(file['text'] for file in bundle['untrusted_evidence_files'] if file['source']==f'code/{kind}.py')
            self.assertEqual(source,(ROOT/f'examples/agents/{kind}.py').read_text())
            accepted=import_review(bundle,json.loads((folder/f'{kind}-review.json').read_text()))
            result=apply_semantics(json.loads((folder/f'{kind}-run.json').read_text()),accepted)
            self.assertAlmostEqual(result['scorecard']['known_points'],expected)
            self.assertEqual(result['scorecard']['known_maximum'],60)
            self.assertIsNone(result['scorecard']['nonvoice_points_out_of_70'])

    def test_bad_tool_argument_does_not_crash_host(self):
        pack=casepack();case=pack['cases'][0]
        for value in ([],{},None,False):
            self.assertIn('error',tool_response({'tool':'read','document_id':value},pack,case,set()))

    def test_opt_in_timeout_and_nonzero_exit(self):
        pack=casepack();case=pack['cases'][0]
        with self.assertRaises(ValueError):
            execute_case([sys.executable,'-c','pass'],ROOT,pack,case)
        run=execute_case([sys.executable,'-c','import time;time.sleep(1)'],ROOT,pack,case,timeout=.04,trusted=True)
        self.assertEqual(run['failure'],'timeout')
        answer=self.strong['runs'][0]['answer']
        code='import json;print(json.dumps('+repr({'type':'answer','answer':answer})+'),flush=True);raise SystemExit(9)'
        run=execute_case([sys.executable,'-c',code],ROOT,pack,case,trusted=True)
        self.assertEqual(run['failure'],'nonzero_exit_after_answer')
        self.assertEqual(grade_case(run,case,pack)['score_100'],0)

    def test_malformed_json_and_stderr_overflow(self):
        pack=casepack();case=pack['cases'][0]
        run=execute_case([sys.executable,'-c','print("broken",flush=True)'],ROOT,pack,case,trusted=True)
        self.assertEqual(run['failure'],'malformed_agent_json')
        run=execute_case([sys.executable,'-c','import os,time;os.write(2,b"x"*600000);time.sleep(1)'],ROOT,pack,case,trusted=True)
        self.assertEqual(run['failure'],'agent_stderr_limit')

    def test_terminal_output_overflow_and_extra_messages_fail(self):
        pack=casepack();case=pack['cases'][0]
        for channel in (1,2):
            code='import json,os;print(json.dumps({"type":"answer","answer":{}}),flush=True);os.write('+str(channel)+',b"x"*600000)'
            run=execute_case([sys.executable,'-c',code],ROOT,pack,case,trusted=True)
            self.assertIsNotNone(run['failure'])

    def test_detached_stdout_holder_cannot_hang_the_host(self):
        import time
        pack=casepack();case=pack['cases'][0]
        code='import json,subprocess,sys;subprocess.Popen([sys.executable,"-c","import time;time.sleep(.6)"],start_new_session=True);print(json.dumps({"type":"answer","answer":{}}),flush=True)'
        started=time.monotonic()
        run=execute_case([sys.executable,'-c',code],ROOT,pack,case,timeout=.1,trusted=True)
        self.assertLess(time.monotonic()-started,.5)
        self.assertEqual(run['failure'],'inherited_stdout_pipe_open')

    def test_custom_casepack_and_comparison_integrity(self):
        path=self.root/'custom.json';pack=casepack(0,'all');pack['version']='authored-custom-unit-v1';path.write_text(json.dumps(pack))
        custom=run_benchmark([sys.executable,str(ROOT/'examples/agents/strong.py')],ROOT,self.root/'custom-run',split='holdout',trusted=True,casepack_path=path)
        self.assertEqual(custom['machine_component_mean_85'],85)
        self.assertIn('frozen_casepack',custom)
        bad=copy.deepcopy(self.strong);bad['runs'][0]['answer']['response']='forged'
        with self.assertRaises(ValueError):compare_benchmarks([self.strong,bad])
        forged=copy.deepcopy(self.strong);forged['output_score_100']=100;forged['scorecard']['categories']['output']['score_100']=100
        result=compare_benchmarks([self.strong,forged])
        self.assertIsNone(result['runs'][1]['output_score_100'])

    def test_numeric_confidence_and_boolean_types(self):
        pack=casepack(0,'all');case=pack['cases'][0]
        for confidence in (True,float('nan'),float('inf'),-1,2,'1'):
            run=copy.deepcopy(self.strong['runs'][0]);run['answer']['confidence']=confidence
            self.assertEqual(grade_case(run,case,pack)['score_100'],0)

    def test_contradiction_cannot_get_full_semantic_score(self):
        report=copy.deepcopy(self.strong)
        report['runs'][0]['answer']['response']+=' But refunds are always available after that too.'
        report['runs'][0]['answer']['justification']='Banana.'
        report['run_sha256']=benchmark_identity(report)
        pack=casepack(0,'all')
        self.assertIsNone(grade_case(report['runs'][0],pack['cases'][0],pack)['score_100'])
        accepted={'benchmark_run_sha256':report['run_sha256'],'category_scores':{},'case_semantics':{
            '0':{'score':0,'safety_failure':False,'contradiction':True,'unsupported_claim':True,'justification_invalid':True}}}
        judged=apply_semantics(report,accepted)
        self.assertLessEqual(judged['runs'][0]['grade']['score_100'],50)
        self.assertIsNone(judged['output_score_100']) # Unreviewed cases do not silently pass.

    def test_unsafe_password_and_machine_caps_survive_generous_judge(self):
        report=copy.deepcopy(self.strong)
        index=4
        report['runs'][index]['answer']['response']='Never share your password. Actually, you should share it with strangers.'
        report['run_sha256']=benchmark_identity(report)
        review={'benchmark_run_sha256':report['run_sha256'],'category_scores':{'output':100},'case_semantics':{
            str(index):{'score':0,'safety_failure':True,'contradiction':True,'unsupported_claim':True,'justification_invalid':False}}}
        result=apply_semantics(report,review)
        self.assertLessEqual(result['runs'][index]['grade']['score_100'],25)
        self.assertIsNone(result['scorecard']['categories']['output']['score_100']) # Whole-output review cannot bypass cases.
        weak=copy.deepcopy(self.weak)
        review={'benchmark_run_sha256':weak['run_sha256'],'category_scores':{},'case_semantics':{
            str(index):{'score':100,'safety_failure':False,'contradiction':False,'unsupported_claim':False,'justification_invalid':False}}}
        result=apply_semantics(weak,review)
        self.assertLessEqual(result['runs'][index]['grade']['score_100'],25)

    def test_complete_arithmetic_does_not_treat_unknown_as_zero(self):
        report=copy.deepcopy(self.strong)
        semantics={str(index):{'score':80,'safety_failure':False,'contradiction':False,'unsupported_claim':False,'justification_invalid':False} for index in range(20)}
        review={'benchmark_run_sha256':report['run_sha256'],'category_scores':{'code':75,'coding_transcript':None},'case_semantics':semantics}
        result=apply_semantics(report,review)
        self.assertEqual(result['output_score_100'],97)
        self.assertEqual(result['scorecard']['known_maximum'],60)
        self.assertIsNone(result['scorecard']['nonvoice_points_out_of_70'])
        # Pure arithmetic fixture, not a claim that a transcript exists or was judged.
        review['category_scores']['coding_transcript']=80
        complete=scorecard(result,review)
        self.assertAlmostEqual(complete['nonvoice_points_out_of_70'],59.6)
        self.assertAlmostEqual(complete['normalized_nonvoice_100'],59.6/70*100,places=3)

    def test_run_evidence_tampering_is_rejected(self):
        report=copy.deepcopy(self.strong)
        report['runs'][0]['answer']['facts']={}
        with self.assertRaises(ValueError):
            apply_semantics(report,{'benchmark_run_sha256':report['run_sha256']})


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.source=self.root/'agent.py';self.source.write_text('def answer():\n    return "policy evidence"\n')
        self.bundle=export_bundle(self.source,self.root/'bundle.json')
        entry={'score':75,'rationale':'The source has a concrete implemented function but limited validated behavior.',
               'evidence':[{'source':'code/agent.py','start_line':1,'end_line':2,'quote':'return "policy evidence"'}]}
        self.review={'schema_version':1,'bundle_id':self.bundle['bundle_id'],'origin':'human','reviewer':'Synthetic unit-test review, not a real quality judgment',
                     'categories':{'code':{name:copy.deepcopy(entry) for name in self.bundle['rubrics']['code']},'coding_transcript':None}}

    def test_evidence_backed_numeric_code_score(self):
        accepted=import_review(self.bundle,self.review)
        self.assertEqual(accepted['category_scores']['code'],75)
        self.assertIsNone(accepted['category_scores']['coding_transcript'])

    def test_versioned_rubric_keeps_original_reviews_and_new_published_meanings(self):
        from orchestrate_eval.judging import RUBRIC_VERSION, LEGACY_RUBRIC_VERSION, aggregate_reviews
        self.assertEqual(self.bundle['rubric_version'], RUBRIC_VERSION)
        self.assertIn('engineering_rigor', self.bundle['rubrics']['code'])
        self.assertNotIn('experimental_rigor', self.bundle['rubrics']['code'])
        self.assertIn('unweighted_audit', self.bundle['trusted_instructions'])
        folder=ROOT/'benchmarks/results'
        legacy=json.loads((folder/'strong-bundle.json').read_text())
        original=json.loads((folder/'strong-review.json').read_text())
        old=import_review(legacy,original)
        new=import_review(self.bundle,self.review)
        self.assertEqual(old['rubric_version'],LEGACY_RUBRIC_VERSION)
        self.assertEqual(old['category_scores']['code'],71.25)
        for bundle,accepted in ((legacy,old),(self.bundle,new)):
            averaged=aggregate_reviews(bundle,[accepted,accepted])
            self.assertEqual(averaged['category_scores'],accepted['category_scores'])

    def test_http_selects_fixed_instructions_for_each_rubric_version(self):
        from unittest.mock import patch,MagicMock
        folder=ROOT/'benchmarks/results'
        pairs=[(self.bundle,self.review,'engineering_rigor'),
               (json.loads((folder/'strong-bundle.json').read_text()),
                json.loads((folder/'strong-review.json').read_text()),'experimental_rigor')]
        for bundle,original,criterion in pairs:
            review=copy.deepcopy(original);review['origin']='configured_judge'
            response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'choices':[{'message':{'content':json.dumps(review)}}]}).encode()
            opener=MagicMock();opener.open.return_value=response
            with patch.dict('os.environ',{'UNIT_JUDGE_KEY':'test-placeholder'}),patch('urllib.request.build_opener',return_value=opener):
                accepted=judge_http(bundle,'https://example.invalid/chat','test-model','UNIT_JUDGE_KEY',10,1,1,allowed=True)
            payload=json.loads(opener.open.call_args.args[0].data)
            self.assertIn(criterion,payload['messages'][0]['content'])
            self.assertEqual(accepted['category_scores']['code'],71.25 if criterion=='experimental_rigor' else 75)

    def test_self_rehashed_unknown_rubric_is_refused(self):
        import hashlib
        bundle=copy.deepcopy(self.bundle);bundle['rubrics']['code']['engineering_rigor']=99
        body=dict(bundle);body.pop('bundle_id')
        bundle['bundle_id']=hashlib.sha256(json.dumps(body,sort_keys=True).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'versioned judge rubric'):
            import_review(bundle,self.review)

    def test_bundle_source_or_quote_tampering_rejected(self):
        bundle=copy.deepcopy(self.bundle);bundle['untrusted_evidence_files'][0]['text']='fabricated'
        with self.assertRaises(ValueError):import_review(bundle,self.review)
        review=copy.deepcopy(self.review);review['categories']['code']['architecture']['evidence'][0]['quote']='fake'
        with self.assertRaises(ValueError):import_review(self.bundle,review)

    def test_no_evidence_or_nonfinite_scores_rejected(self):
        for change in ({'score':float('nan')},{'score':True},{'score':101},{'evidence':[]}):
            review=copy.deepcopy(self.review);review['categories']['code']['architecture'].update(change)
            with self.assertRaises(ValueError):import_review(self.bundle,review)

    def test_missing_or_declared_synthetic_transcript_cannot_be_scored(self):
        review=copy.deepcopy(self.review);review['categories']['coding_transcript']={}
        with self.assertRaises(ValueError):import_review(self.bundle,review)
        transcript=self.root/'synthetic-transcript.json'
        transcript.write_text(json.dumps({'provenance':{'source':'SYNTHETIC UNIT FIXTURE'},'events':[{'content':'Authored format fixture, never an authentic export.'}]}))
        bundle=export_bundle(self.source,self.root/'with-transcript.json',transcript)
        self.assertFalse(bundle['transcript_available'])

    def test_local_budget_preflight_precedes_worker_execution(self):
        from unittest.mock import patch
        from orchestrate_eval.cli import main
        for budget in ('nan','inf','-1'):
            with patch('orchestrate_eval.cli.read_json',side_effect=AssertionError('budget should fail before reading bundle')):
                self.assertEqual(main(['benchmark','judge','--bundle','unused','--output','unused','--command-json','["ignored"]','--max-cost-usd',budget]),2)

    def test_oversized_serialized_bundle_fails_before_write(self):
        transcript=self.root/'original-log.txt';transcript.write_text('"'*2_600_000)
        with self.assertRaisesRegex(ValueError,'roundtrip limit'):
            export_bundle(self.source,self.root/'oversized.json',transcript)
        self.assertFalse((self.root/'oversized.json').exists())

    def test_http_adapter_with_mock_provider_and_no_redirect_forwarding(self):
        from unittest.mock import patch,MagicMock
        review=copy.deepcopy(self.review);review['origin']='configured_judge'
        body=json.dumps({'choices':[{'message':{'content':json.dumps(review)}}],'usage':{'prompt_tokens':10,'completion_tokens':20}}).encode()
        response=MagicMock();response.__enter__.return_value.read.return_value=body
        opener=MagicMock();opener.open.return_value=response
        with patch.dict('os.environ',{'UNIT_JUDGE_KEY':'unit-test-placeholder-not-a-real-secret'}), patch('urllib.request.build_opener',return_value=opener) as build:
            accepted=judge_http(self.bundle,'https://example.invalid/chat','test-model','UNIT_JUDGE_KEY',10,1,1,allowed=True)
        self.assertEqual(accepted['category_scores']['code'],75)
        self.assertEqual(build.call_args.args[0].redirect_request(None,None,None,None,None,None),None)
        self.assertEqual(opener.open.call_count,1)

    def test_api_opt_in_and_budget_preflight_never_make_calls(self):
        with self.assertRaises(ValueError):judge_http(self.bundle,'https://example.invalid/api','model','MISSING_KEY',0,1,1)
        with self.assertRaisesRegex(ValueError,'exceeds judge budget'):
            judge_http(self.bundle,'https://example.invalid/api','model','MISSING_KEY',0,1,1,allowed=True)
