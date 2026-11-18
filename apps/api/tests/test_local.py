"""Local onboarding checks against an isolated database."""
from fastapi.testclient import TestClient
from app.main import app

def test_local_account_lifecycle():
    with TestClient(app, headers={'X-Cognify-Request':'1'}) as client:
        assert client.get('/api/v1/health/ready').status_code == 200
        assert client.get('/api/v1/me').status_code == 401
        credentials = {'email':'local@example.test','password':'testing-password-123','adult':True}
        assert client.post('/api/v1/auth/register', json=credentials).status_code == 201
        assert client.get('/api/v1/me').status_code == 200
        profile = {'alias':'Explorer','age':'18+','avatar':'🌱','companion':'Nova'}
        assert client.post('/api/v1/learners', json=profile).status_code == 201
        assert len(client.get('/api/v1/learners').json()) == 1
        assert client.post('/api/v1/learners', json={**profile,'age':'8–14'}).status_code == 409
        assert client.post('/api/v1/auth/logout', json={}).status_code == 200
        assert client.get('/api/v1/learners').status_code == 401
        assert client.post('/api/v1/auth/login', json=credentials).status_code == 200
        assert len(client.get('/api/v1/learners').json()) == 1

def test_csrf_origin_gate():
    with TestClient(app) as client:
        assert client.post('/api/v1/auth/register', json={}).status_code == 403
        assert client.post('/api/v1/auth/register', headers={'X-Cognify-Request':'1','Origin':'https://untrusted.example'}, json={}).status_code == 403
