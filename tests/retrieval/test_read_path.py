import asyncio
from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings
from kivi.services import drain
from kivi.storage import connect

class Extractor:
    async def extract(self, text):
        return [{'type':'entity','name':'Atlas','relation':'owner','value':'Arun','basis':'stated'}]

def client(tmp_path):
    app=create_app(Settings(database_path=str(tmp_path/'kivi.db')), Extractor())
    with TestClient(app) as c:
        yield c, app

def seed(c):
    response=c.post('/v1/dictations',json={'raw_asr':'Atlas owner Arun','formatted_text':'Atlas owner Arun'}); assert response.status_code==202
    return response.json()

def test_grounded_recall_and_no_match_abstains(tmp_path):
    for c,_ in client(tmp_path):
        seed(c)
        found=c.post('/v1/hey-kivi',json={'text':'Who owns Atlas?'}).json()
        assert found['selected_tool']=='recall_search' and found['citations'] and found['status']=='completed'
        missing=c.post('/v1/hey-kivi',json={'text':'What did Arun say about auth migration?'}).json()
        assert missing['status']=='abstained' and missing['reason']=='NO_GROUNDED_MATCH'

def test_permissions_do_not_change_candidate_order(tmp_path):
    for c,_ in client(tmp_path):
        seed(c); anbu=c.post('/v1/hey-kivi',json={'text':'Atlas'}).json()
        c.put('/v1/permissions',json={'mode':'koottu'}); koottu=c.post('/v1/hey-kivi',json={'text':'Atlas'}).json()
        def candidates(trace_id):
            db=connect(Settings(database_path=str(tmp_path/'kivi.db')))
            try: return [x['memory_id'] for x in db.execute('SELECT memory_id FROM retrieval_candidates WHERE trace_id=? ORDER BY rank',(trace_id,))]
            finally: db.close()
        assert candidates(anbu['trace_id'])==candidates(koottu['trace_id'])
