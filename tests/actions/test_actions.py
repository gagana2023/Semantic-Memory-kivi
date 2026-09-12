from fastapi.testclient import TestClient
from kivi.app import create_app
from kivi.config import Settings

class Extractor:
    async def extract(self, text):
        return [{'type':'preference','name':'Meera','relation':'signoff','value':'Best, Meera','basis':'observed'}]

def test_confirm_correct_forget_pin_and_idempotency(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path/'kivi.db')), Extractor())) as c:
        c.post('/v1/dictations', json={'raw_asr':'x','formatted_text':'x'})
        memory=c.get('/v1/memories').json()['groups']['observed'][0]; mid=memory['id']
        version=memory['version']
        confirmed=c.post(f'/v1/memories/{mid}/actions',json={'action':'confirm','expected_version':version,'idempotency_key':'confirm'}).json()
        assert confirmed['memory']['basis']=='stated'
        repeat=c.post(f'/v1/memories/{mid}/actions',json={'action':'confirm','expected_version':version,'idempotency_key':'confirm'}).json()
        assert repeat['receipt_id']==confirmed['receipt_id']
        stale=c.post(f'/v1/memories/{mid}/actions',json={'action':'pin','expected_version':version,'idempotency_key':'stale'})
        assert stale.status_code==409
        corrected=c.post(f'/v1/memories/{mid}/actions',json={'action':'correct','expected_version':1,'idempotency_key':'correct','value':'Regards, Meera'}).json()
        assert corrected['memory']['value']=='Regards, Meera'
        forgotten=c.post(f'/v1/memories/{mid}/actions',json={'action':'forget','expected_version':2,'idempotency_key':'forget'}).json()
        assert forgotten['memory']['status']=='suppressed'
        assert c.get(f'/v1/memories/{mid}').status_code==404

def test_negative_action_requires_version_and_content(tmp_path):
    with TestClient(create_app(Settings(database_path=str(tmp_path/'kivi.db')), Extractor())) as c:
        c.post('/v1/dictations',json={'raw_asr':'x','formatted_text':'x'}); mid=c.get('/v1/memories').json()['groups']['observed'][0]['id']
        assert c.post(f'/v1/memories/{mid}/actions',json={'action':'correct','expected_version':0,'idempotency_key':'x'}).status_code==422
