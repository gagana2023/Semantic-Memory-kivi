import json
import sys

import pytest
from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings
from kivi.evaluation import create_run, run_complete
from kivi.storage import connect

def test_evaluation_is_durable_has_fixed_evidence_and_does_not_create_transcripts(tmp_path):
    settings=Settings(database_path=str(tmp_path/'kivi.db'))
    with TestClient(create_app(settings)) as client:
        queued=client.post('/v1/evaluations',json={'case_set':'development'})
        assert queued.status_code==202
        result=client.get(queued.json()['status_url']+'?wait=true').json()['report']
        assert result['completeness']['all_position_claims_have_evidence']
        assert result['completeness']['all_criteria_have_evidence']
        assert result['completeness']['evaluation_questions_absent_from_transcripts']
        assert not result['passed']
        assert any(x['case_id']=='negative:absent_history_answer_must_fail' and x['outcome']=='failed' for x in result['results'])
    db=connect(settings)
    assert db.execute('SELECT COUNT(*) FROM transcripts').fetchone()[0]==0
    assert db.execute('SELECT COUNT(*) FROM evaluation_results').fetchone()[0]==40
    db.close()

def test_unknown_case_set_fails_loudly(tmp_path):
    settings=Settings(database_path=str(tmp_path/'kivi.db'))
    try: create_run(settings,'missing')
    except ValueError as exc: assert str(exc)=='EVALUATION_CASE_SET_NOT_FOUND'
    else: raise AssertionError('unknown evaluation case set must not fabricate a run')

class EmptyExtractor:
    async def extract(self, text): return []

def test_complete_runner_emits_full_audit_from_clean_database(tmp_path):
    settings=Settings(database_path=str(tmp_path/'complete.db'))
    report=run_complete(settings,'fixtures/development-500.json','EVAL_QUESTIONS.json','GROUND_TRUTH.json',tmp_path,EmptyExtractor(),sample_every=100)
    assert len(report['ingestion'])==500
    assert len(report['questions'])==52
    assert report['database_growth'][0]['records_processed']==1
    assert report['database_growth'][-1]['records_processed']==500
    assert report['summary']['unanswerable']=={'correct_refusals':11,'fabrications':0}
    assert (tmp_path/'results.json').is_file()
    assert '## Failures (full)' in (tmp_path/'summary.md').read_text(encoding='utf-8')

def test_evaluate_cli_prints_completion_signal_and_artifact_paths(tmp_path, monkeypatch, capsys):
    from kivi import __main__
    monkeypatch.setattr(__main__, 'run_complete', lambda *args: {'summary': {'passed': 2, 'total': 2}})
    monkeypatch.setattr(sys, 'argv', ['python -m kivi', 'evaluate', '--output-dir', str(tmp_path)])
    __main__.main()
    receipt=json.loads(capsys.readouterr().out)
    assert receipt == {
        'status': '✅ Evaluation complete',
        'passed': 2,
        'total': 2,
        'files_created': [str(tmp_path / 'results.json'), str(tmp_path / 'summary.md')],
    }

def test_evaluate_cli_reports_completed_run_before_failed_exit(tmp_path, monkeypatch, capsys):
    from kivi import __main__
    monkeypatch.setattr(__main__, 'run_complete', lambda *args: {'summary': {'passed': 1, 'total': 2}})
    monkeypatch.setattr(sys, 'argv', ['python -m kivi', 'evaluate', '--output-dir', str(tmp_path)])
    with pytest.raises(SystemExit, match='1'):
        __main__.main()
    receipt=json.loads(capsys.readouterr().out)
    assert receipt['status'] == '⚠️ Evaluation complete: some checks failed'
    assert receipt['files_created'] == [str(tmp_path / 'results.json'), str(tmp_path / 'summary.md')]
