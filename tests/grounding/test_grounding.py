from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self,text): return []

def test_draft_does_not_claim_recipient_context(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path/'kivi.db')),Extractor())) as c:
        result=c.post('/v1/hey-kivi',json={'text':'draft reply','context':"Priya's mother is in hospital"}).json()
        assert result['status']=='abstained' and 'hospital' not in str(result)
