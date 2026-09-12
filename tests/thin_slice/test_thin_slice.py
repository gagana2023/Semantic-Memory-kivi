import time
from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings
from kivi.services import ExtractionError
class Extractor:
    async def extract(self,text):
        if text=='invalid': raise ExtractionError('OLLAMA_EXTRACTION_FAILED')
        return {'name':'Atlas','relation':'review note','value':'ready'}
def app(tmp_path): return create_app(Settings(database_path=str(tmp_path/'kivi.db')),Extractor())
def wait(client,job):
    for _ in range(50):
        state=client.get('/v1/jobs/'+job).json()['state']
        if state in ('completed','failed'): return state
        time.sleep(.01)
    raise AssertionError('job did not finish')
def test_ac_fr_01_identical_text_has_explicit_modes(tmp_path):
    with TestClient(app(tmp_path)) as c:
        d=c.post('/v1/dictations',json={'raw_asr':'Find my Atlas review note','formatted_text':'Find my Atlas review note'}); h=c.post('/v1/hey-kivi',json={'text':'Find my Atlas review note'})
        assert d.status_code==202 and d.json()['mode']=='dictation'; assert h.json()['mode']=='hey_kivi'
def test_ac_fr_03_response_precedes_completion_and_persists_recall(tmp_path):
    settings=Settings(database_path=str(tmp_path/'kivi.db'))
    with TestClient(create_app(settings,Extractor())) as c:
        response=c.post('/v1/dictations',json={'raw_asr':'Atlas review','formatted_text':'Atlas review'}); assert response.status_code==202
        body=response.json(); assert body['written_response']=='Atlas review' and body['semantic_processing']=='semantic_processing'; assert wait(c,body['job_id'])=='completed'
        recalled=c.post('/v1/hey-kivi',json={'text':'Atlas'}).json(); assert recalled['citations'] and recalled['tool']=='recall_search'
        inspected=c.get('/v1/inspect/'+body['transcript_id']).json(); assert inspected['memories'][0]['transcript_id']==body['transcript_id'] and inspected['why']
    with TestClient(create_app(settings,Extractor())) as c: assert c.post('/v1/hey-kivi',json={'text':'Atlas'}).json()['citations']
def test_negative_invalid_request_and_extraction_failure_are_not_fabricated(tmp_path):
    with TestClient(app(tmp_path)) as c:
        assert c.post('/v1/dictations',json={'raw_asr':'x'}).status_code==422
        response=c.post('/v1/dictations',json={'raw_asr':'invalid','formatted_text':'invalid'}).json(); assert wait(c,response['job_id'])=='failed'
        assert c.post('/v1/hey-kivi',json={'text':'nothing'}).json()['answer']==["I don't have a matching stated memory."]
