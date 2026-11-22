import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scripts.validate_project import validate_manifest
from scripts.creative_quality import REVIEW_KEYS
ROOT=Path(__file__).resolve().parents[1]
NOW='2026-11-20T16:00:00+08:00'


def mock_complete():
    """Synthetic records, not evidence of real software use or licenses."""
    d=json.loads((ROOT/'tests/fixtures/mock_project.json').read_text())
    d['script'].update(hook_candidates=[dict(hook_id=str(i),kind=k,text='虚构开头'+str(i),visual_proof='测试录屏',proof_status='ready',appeal_reason='测试') for i,k in enumerate(['结果','反差','悬念'])],selected_hook_id='0',selection_reason='测试')
    d['script']['hook']=d['script']['hook_candidates'][0]['text']
    d['script']['beats']=[dict(text='先看结果。',emotion='惊讶',pause_after_ms=300),dict(text='看看怎么做。',emotion='解释',pause_after_ms=0)]
    s=d['director']['shots'][0]
    s.update(opening_result=True,caption_style='关键词强调',motion='高亮推进',transition='元素承接',music='低音量背景',sfx='轻提示',voice_emotion='惊讶转解释')
    s['asset'].update(status='ready',path='clip.mp4')
    d['editing'].update(status='qa_pass',engine='jianying_desktop',render_path='out.mp4',editable_project_path='project',export_evidence='虚构导出记录',preflight=dict(status='passed',checked_at=NOW,app_version='mock',operation_evidence='虚构操作记录',resources=[dict(kind=k,name='虚构资源',free=True,license_scope='测试许可',license_status='verified',evidence='虚构证据',checked_at=NOW) for k in ['voice','caption','transition','music','sfx']]),technical_qa=dict(status='passed'),human_review=dict(status='passed',reviewer='mock',reviewed_at=NOW),creative_review=dict(status='passed',reviewer='mock',reviewed_at=NOW,render_path='out.mp4',render_sha256='0'*64,checks={k:dict(status='passed',evidence='00:00–00:03 虚构观察',issues=[]) for k in REVIEW_KEYS}),rework_log=[])
    d['delivery']['status']='ready'
    return d


class CreativeGatesTests(unittest.TestCase):
    def test_complete_mock_records_pass(self):
        self.assertEqual(validate_manifest(mock_complete(),stage='final'),[])

    def test_legacy_readable_but_not_production_ready(self):
        d=json.loads((ROOT/'tests/fixtures/mock_project.json').read_text())
        self.assertEqual(validate_manifest(d),[])
        self.assertTrue(validate_manifest(d,stage='script'))
        self.assertTrue(validate_manifest(d,stage='final'))

    def test_bad_hooks_stop_editing(self):
        for mutation in ['missing','duplicate','pending','mismatched']:
            d=mock_complete()
            if mutation=='missing':d['script']['hook_candidates'].pop()
            if mutation=='duplicate':d['script']['hook_candidates'][1]['kind']='结果'
            if mutation=='pending':d['script']['hook_candidates'][0]['proof_status']='pending'
            if mutation=='mismatched':d['script']['hook']='另一个钩子'
            with self.subTest(mutation=mutation):self.assertTrue(validate_manifest(d,stage='edit'))

    def test_monotone_no_pause_fails(self):
        d=mock_complete()
        for b in d['script']['beats']:b.update(emotion='解释',pause_after_ms=0)
        self.assertTrue(validate_manifest(d,stage='script'))

    def test_shot_design_fields_required(self):
        for key in ['visual_source','caption','caption_style','motion','transition','music','sfx','voice_emotion']:
            d=mock_complete();d['director']['shots'][0].pop(key)
            with self.subTest(key=key):self.assertTrue(validate_manifest(d,stage='director'))

    def test_title_card_opening_fails(self):
        d=mock_complete();d['director']['shots'][0]['opening_result']=False
        self.assertTrue(validate_manifest(d,stage='director'))

    def test_remotion_default_requires_real_autonomous_review_at_final(self):
        d=mock_complete();d['editing']['engine']='remotion'
        d['editing']['preflight']['resources']=[r for r in d['editing']['preflight']['resources'] if r['kind'] in ('voice','caption')]
        d['delivery'].update(manual_publish_only=True,published=False)
        # Edit-stage checks can run before exporting; a completed project triggers full QA even for --stage edit.
        d['editing']['status']='not_started'
        d['delivery']['status']='pending'
        self.assertEqual(validate_manifest(d,stage='edit'),[])
        d['editing']['status']='qa_pass'
        d['delivery']['status']='ready'
        self.assertTrue(any('自动审查' in e or '音画' in e for e in validate_manifest(d,stage='final')))
        d['editing']['automated_review']=dict(status='passed',reviewer='Codex 实际音画复核',reviewed_at=NOW,evidence='00:00-00:03 口播与画面内容同步')
        self.assertEqual(validate_manifest(d,stage='final'),[])

    def test_unknown_engine_requires_explicit_choice(self):
        d=mock_complete();d['editing']['engine']='other_engine'
        self.assertTrue(validate_manifest(d,stage='edit'))

    def test_resources_need_free_status_license_time_and_operation_evidence(self):
        for mutation in ['missing','paid','license','time','operation']:
            d=mock_complete();p=d['editing']['preflight']
            if mutation=='missing':p['resources'].pop()
            if mutation=='paid':p['resources'][0]['free']=False
            if mutation=='license':p['resources'][0]['license_scope']=''
            if mutation=='time':p['checked_at']='2026-11-20'
            if mutation=='operation':p['operation_evidence']=None
            with self.subTest(mutation=mutation):self.assertTrue(validate_manifest(d,stage='edit'))

    def test_blocked_editor_stops(self):
        d=mock_complete();d['editing']['status']='blocked'
        self.assertTrue(validate_manifest(d,stage='edit'))

    def test_each_creative_failure_blocks_delivery(self):
        for key in REVIEW_KEYS:
            for status in ['failed','not_run']:
                d=mock_complete();d['editing']['creative_review']['checks'][key]['status']=status
                with self.subTest(key=key,status=status):self.assertTrue(validate_manifest(d))

    def test_stale_review_and_open_rework_block_delivery(self):
        d=mock_complete();d['editing']['creative_review']['render_path']='old.mp4'
        self.assertTrue(validate_manifest(d))
        d=mock_complete();d['editing']['rework_log']=[dict(issue='机械音',action='重配',status='open')]
        self.assertTrue(validate_manifest(d))

    def test_export_evidence_and_real_files_required(self):
        d=mock_complete();d['editing']['export_evidence']=None
        self.assertTrue(validate_manifest(d,stage='final'))
        with tempfile.TemporaryDirectory() as folder:
            self.assertTrue(validate_manifest(mock_complete(),root=Path(folder),check_files=True,stage='final'))

    def test_cli_failure_and_success_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'manifest.json'
            for valid in [False,True]:
                d=mock_complete()
                if not valid:d['editing']['creative_review']['checks']['voice']['status']='failed'
                p.write_text(json.dumps(d))
                result=subprocess.run([sys.executable,'-B',str(ROOT/'scripts/validate_project.py'),str(p),'--stage','final'],capture_output=True,text=True)
                self.assertEqual(result.returncode,0 if valid else 1)
                self.assertEqual(json.loads(result.stdout)['valid'],valid)

    def test_malformed_fields_rejected(self):
        for key,value in [('hook_candidates',[None]),('beats',[False])]:
            d=mock_complete();d['script'][key]=value
            self.assertTrue(validate_manifest(d,stage='final'))

    def test_same_filename_reexport_invalidates_review(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'clip.mp4').write_bytes(b'fake source')
            (root/'project').mkdir()
            render=root/'out.mp4'
            render.write_bytes(b'fake v1; test does not inspect media')
            d=mock_complete()
            d['editing']['creative_review']['render_sha256']=hashlib.sha256(render.read_bytes()).hexdigest()
            self.assertEqual(validate_manifest(d,root=root,check_files=True,stage='final'),[])
            render.write_bytes(b'fake v2')
            self.assertTrue(any('SHA256' in e for e in validate_manifest(d,root=root,check_files=True,stage='final')))

    def test_explicit_stage_cannot_bypass_failed_final_review(self):
        d=mock_complete();d['editing']['creative_review']['checks']['voice']['status']='failed'
        self.assertTrue(validate_manifest(d,stage='script'))

    def test_unknown_license_or_malformed_rework_rejected(self):
        d=mock_complete();d['editing']['preflight']['resources'][0]['license_status']='unknown'
        self.assertTrue(validate_manifest(d))
        d=mock_complete();d['editing']['rework_log']={'status':'open'}
        self.assertTrue(validate_manifest(d))

    def test_verified_license_cannot_have_unknown_scope(self):
        d=mock_complete();d['editing']['preflight']['resources'][0]['license_scope']='unknown'
        self.assertTrue(validate_manifest(d,stage='final'))
