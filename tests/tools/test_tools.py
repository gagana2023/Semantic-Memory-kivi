from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self,text): return [{'type':'episode','name':'Atlas','relation':'review','value':'Thursday','basis':'stated'}]

def test_only_three_tools_and_schedule_idempotency(tmp_path):
    app=create_app(Settings(database_path=str(tmp_path/'kivi.db')),Extractor())
    with TestClient(app) as c:
        c.post('/v1/dictations',json={'raw_asr':'Atlas review Thursday','formatted_text':'Atlas review Thursday'})
        assert c.post('/v1/hey-kivi',json={'text':'web search Atlas'}).json()['status']=='unsupported'
        payload={'text':'reschedule Atlas to 2026-10-01T10:00:00Z','idempotency_key':'same'}
        one=c.post('/v1/hey-kivi',json=payload).json(); two=c.post('/v1/hey-kivi',json=payload).json()
        assert one['event_id']==two['event_id'] and one['external_side_effects']=='none'
        assert c.post('/v1/hey-kivi',json={'text':'schedule Atlas'}).json()['status']=='abstained'
