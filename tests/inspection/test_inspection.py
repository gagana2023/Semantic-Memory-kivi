from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self,text): return [{'type':'entity','name':'Atlas','relation':'owner','value':'Arun','basis':'stated'}]

def test_memory_detail_history_and_why(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path/'kivi.db')),Extractor())) as c:
        d=c.post('/v1/dictations',json={'raw_asr':'x','formatted_text':'x'}).json(); mid=c.get('/v1/memories').json()['groups']['stated'][0]['id']
        detail=c.get(f'/v1/memories/{mid}').json(); assert detail['provenance'] and detail['history']
        h=c.post('/v1/hey-kivi',json={'text':'Atlas'}).json(); why=c.get(f"/v1/why/{h['trace_id']}").json()
        assert why['trace'] and why['candidates']
        transcript=c.get(f"/v1/inspect/{d['transcript_id']}").json(); assert transcript['transcript']['outcome']=='stored_candidates'
