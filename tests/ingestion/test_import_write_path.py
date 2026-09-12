import time
from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self, text):
        if text == 'timeout': raise __import__('kivi.services',fromlist=['ExtractionError']).ExtractionError('OLLAMA_EXTRACTION_FAILED')
        if text == 'excluded': return [{'type':'entity','name':'A','relation':'health','value':'private','basis':'stated'}]
        return [{'type':'entity','name':'Atlas','relation':'owner','value':'Arun','basis':'stated'}, {'type':'episode','name':'Atlas','relation':'review','value':'Thursday','basis':'stated'}]

def record(i,text='ok'):
    return {'transcript_id':f'tr_{i}','raw_asr':text,'formatted_text':text,'occurred_at':f'2026-01-0{i}T10:00:00Z','metadata':{'source':'dictation'}}
def wait(c,url):
    for _ in range(100):
        result=c.get(url).json()
        if result['complete']: return result
        time.sleep(.01)
    raise AssertionError('import did not complete')
def test_ac_fr_04_05_06_07_08_10_12_import_and_safe_drops(tmp_path):
    settings=Settings(database_path=str(tmp_path/'kivi.db'),extraction_retry_cap=1)
    with TestClient(create_app(settings,Extractor())) as c:
        response=c.post('/v1/imports',json={'records':[record(1),record(2,'excluded'),record(3,'timeout')]})
        assert response.status_code==202; body=response.json(); assert body['accepted']==3
        status=wait(c,body['status_url']); assert status['counts']['processed']==2 and status['counts']['quarantined']==1
        inspect=c.get('/v1/inspect/tr_2').json(); assert inspect['memories']==[]
        again=c.post('/v1/imports',json={'records':[record(1)]}); assert again.status_code==202
        conflict=record(1,'changed'); assert c.post('/v1/imports',json={'records':[conflict]}).status_code==409
