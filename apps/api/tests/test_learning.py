"""Exercise real persistence, grading and economic boundaries through HTTP."""
import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.security import _windows

@pytest.fixture
def learner():
    _windows.clear()
    with TestClient(app,headers={'X-Cognify-Request':'1'}) as client:
        assert client.post('/api/v1/auth/register',json={'email':str(uuid.uuid4())+'@test.example','password':'long-test-password','adult':True}).status_code==201
        response=client.post('/api/v1/learners',json={'alias':'Tester','age':'18+','avatar':'🌱','companion':'Nova'})
        assert response.status_code==201
        yield client,response.json()['id']

def complete(client,lid,mode='battle'):
    started=client.post(f'/api/v1/learners/{lid}/attempts',json={'topic':'coding','mode':mode})
    assert started.status_code==201,started.text
    round=started.json()
    while not round['completed']:
        answer=['0','1','2'] if mode=='puzzle' else [str(round['step'])] if mode=='match' else ['0']
        response=client.post('/api/v1/attempts/'+round['id']+'/responses',json={'sequence':round['step'],'answer':answer,'key':str(uuid.uuid4())})
        assert response.status_code==200,response.text
        round=response.json()
    return round

def test_world_and_reward_flow(learner):
    client,lid=learner
    assert len(client.get('/api/v1/topics').json())>=6
    assert client.post(f'/api/v1/learners/{lid}/attempts',json={'topic':'coding','mode':'boss'}).status_code==409
    result=complete(client,lid)
    assert result['rewards']=={'xp':30,'coins':15}
    assert complete(client,lid)['rewards']=={'xp':0,'coins':0}
    complete(client,lid,'puzzle')
    assert complete(client,lid,'boss')['correct']==4
    progress=client.get(f'/api/v1/learners/{lid}/progress').json()
    assert progress['xp']==90 and progress['coins']==45
    assert progress['skills'][0]['accuracy']==100
    assert progress['skills'][0]['evidence']==4
    assert 'Strong foundations' in progress['badges']

def test_receipts_and_private_answers(learner):
    client,lid=learner
    round=client.post(f'/api/v1/learners/{lid}/attempts',json={'topic':'coding'}).json()
    assert 'correct' not in round['challenge']
    assert 'explanation' not in round['challenge']
    payload={'sequence':0,'answer':['0'],'key':str(uuid.uuid4())}
    url=f'/api/v1/attempts/{round["id"]}/responses'
    first=client.post(url,json=payload)
    assert first.status_code==200
    assert client.post(url,json=payload).json()==first.json()
    assert client.post(url,json={**payload,'answer':['1']}).status_code==409
    assert client.post(url,json={**payload,'key':str(uuid.uuid4())}).status_code==409

def test_hints_and_invalid_choices(learner):
    client,lid=learner
    round=client.post(f'/api/v1/learners/{lid}/attempts',json={'topic':'coding'}).json()
    root='/api/v1/attempts/'+round['id']
    assert client.post(root+'/hints',json={}).status_code==200
    assert client.post(root+'/responses',json={'sequence':0,'answer':['999'],'key':str(uuid.uuid4())}).status_code==422
    assert client.post(root+'/responses',json={'sequence':0,'answer':['0'],'key':str(uuid.uuid4())}).status_code==200
    progress=client.get(f'/api/v1/learners/{lid}/progress').json()
    assert progress['skills'][0]['accuracy']==0

def test_purchase_is_idempotent_and_overspend_rejected(learner):
    client,lid=learner
    url=f'/api/v1/learners/{lid}/purchases'
    assert client.post(url,json={'cosmetic':'mint'}).status_code==409
    complete(client,lid)
    complete(client,lid,'puzzle')
    assert client.post(url,json={'cosmetic':'mint'}).status_code==200
    assert client.post(url,json={'cosmetic':'mint'}).status_code==200
    progress=client.get(f'/api/v1/learners/{lid}/progress').json()
    assert progress['coins']==0 and progress['equipped']=='mint'
    assert client.post(url,json={'cosmetic':'ocean'}).status_code==409

def test_isolation_and_delete(learner):
    client,lid=learner
    complete(client,lid)
    with TestClient(app,headers={'X-Cognify-Request':'1'}) as other:
        other.post('/api/v1/auth/register',json={'email':str(uuid.uuid4())+'@test.example','password':'another-password','adult':True})
        for path in ['progress','shop','export','chat']:
            assert other.get(f'/api/v1/learners/{lid}/{path}').status_code==404
        assert other.delete(f'/api/v1/learners/{lid}').status_code==404
    assert client.delete(f'/api/v1/learners/{lid}').status_code==200
    assert client.get(f'/api/v1/learners/{lid}/progress').status_code==404

def test_chat_requests_and_preferences(learner):
    client,lid=learner
    root=f'/api/v1/learners/{lid}'
    assert client.post(root+'/topic-requests',json={'topic':'woodworking'}).json()['status']=='awaiting_configuration'
    assert client.post(root+'/topic-requests',json={'topic':'coding'}).json()['status']=='ready'
    response=client.post(root+'/chat/streams',json={'topic':'coding','message':'Give me an activity'})
    assert 'approved_chunk' in response.text and 'paper airplane' in response.text
    assert client.post(root+'/settings',json={'leaderboard':True}).status_code==200
    assert any(row['you'] for row in client.get(root+'/leaderboard').json())
    assert client.post(root+'/activity',json={}).status_code==200
    assert client.get(root+'/export').json()['profile']['alias']=='Tester'
