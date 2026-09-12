from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings
from kivi.storage import connect

class Extractor:
    async def extract(self,text): return [{'type':'preference','name':'A','relation':'does','value':'B','basis':'observed'}]

def test_old_unpinned_observation_is_not_surfaced(tmp_path):
    settings=Settings(database_path=str(tmp_path/'kivi.db'))
    with TestClient(create_app(settings,Extractor())) as c:
        c.post('/v1/dictations',json={'raw_asr':'x','formatted_text':'x'}); mid=c.get('/v1/memories').json()['groups']['observed'][0]['id']
        db=connect(settings); db.execute("UPDATE memories SET created_at='2000-01-01T00:00:00Z' WHERE id=?",(mid,)); db.commit(); db.close()
        assert c.post('/v1/hey-kivi',json={'text':'A'}).json()['status']=='abstained'
