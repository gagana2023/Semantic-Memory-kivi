from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self,text): return [{'type':'episode','name':'Atlas','relation':'review','value':'Thursday','basis':'stated'}]

def test_action_and_schedule_survive_restart(tmp_path):
    settings=Settings(database_path=str(tmp_path/'kivi.db'))
    with TestClient(create_app(settings,Extractor())) as c:
        c.post('/v1/dictations',json={'raw_asr':'x','formatted_text':'x'}); m=c.get('/v1/memories').json()['groups']['stated'][0]
        c.post(f"/v1/memories/{m['id']}/actions",json={'action':'pin','expected_version':0,'idempotency_key':'pin'})
        c.post('/v1/hey-kivi',json={'text':'schedule Atlas 2026-10-01T10:00:00Z','idempotency_key':'event'})
    with TestClient(create_app(settings,Extractor())) as c:
        assert c.get('/v1/memories').json()['groups']['stated'][0]['pinned']==1
