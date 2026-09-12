from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self,text):
        return [{'type':'preference','name':'Meera','relation':'prose','value':'short','basis':'observed'}]

def test_anbu_withholds_observation_and_koottu_labels_it(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path/'kivi.db')),Extractor())) as c:
        c.post('/v1/dictations',json={'raw_asr':'Meera prose short','formatted_text':'Meera prose short'})
        anbu=c.post('/v1/hey-kivi',json={'text':'Meera prose'}).json()
        assert anbu['status']=='abstained'
        c.put('/v1/permissions',json={'mode':'koottu'})
        koottu=c.post('/v1/hey-kivi',json={'text':'Meera prose'}).json()
        assert koottu['status']=='completed' and koottu['answer'][0].startswith('Kivi noticed:')
