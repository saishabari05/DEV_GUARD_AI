import pytest
import io
import zipfile
from app import create_app
from app.repository.manager import RepositoryManager

@pytest.fixture
def client():
    app = create_app()
    app.config.update({
        "TESTING": True,
    })
    with app.test_client() as client:
        yield client

@pytest.fixture
def sample_workspace():
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("app/__init__.py", "# init")
        zf.writestr("app/auth.py", "def authenticate_user(email):\n    return email\n")
        zf.writestr("tests/test_auth.py", "def test_auth():\n    assert True\n")
    res = RepositoryManager.ingest_zip_repo(zip_buf.getvalue())
    return res["workspace_id"]

def test_health(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json == {"status": "ok", "service": "devguard-backend"}

def test_investigate_valid(client, sample_workspace, monkeypatch):
    monkeypatch.setattr('app.main.investigate', lambda *args: {"status": "ROOT_CAUSE_IDENTIFIED", "success": True, "proposed_patch": {"file": "app/auth.py", "patch": "fix"}})
    monkeypatch.setenv('GEMINI_API_KEY', 'fake_key')
    
    response = client.post('/api/investigate', json={
        "repository": sample_workspace,
        "bug_report": "Users cannot log in when using uppercase emails."
    })
    assert response.status_code == 200
    assert response.json["status"] in ["AWAITING_APPROVAL", "ROOT_CAUSE_IDENTIFIED"]

def test_investigate_missing_bug_report(client, sample_workspace):
    response = client.post('/api/investigate', json={
        "repository": sample_workspace,
        "mode": "directed"
    })
    assert response.status_code == 400

def test_investigate_invalid_repo(client):
    response = client.post('/api/investigate', json={
        "repository": "ws_non_existent",
        "bug_report": "test"
    })
    assert response.status_code == 404

def test_path_traversal(client):
    response = client.post('/api/investigate', json={
        "repository": "../../something",
        "bug_report": "test"
    })
    assert response.status_code == 400

def test_tools_search(client, sample_workspace):
    response = client.post('/api/tools/search', json={
        "repository": sample_workspace,
        "query": "authenticate_user"
    })
    assert response.status_code == 200
    assert response.json["success"] is True
    files = [m["file"] for m in response.json["matches"]]
    assert "app/auth.py" in files

def test_tools_test(client, sample_workspace):
    response = client.post('/api/tools/test', json={
        "repository": sample_workspace
    })
    assert response.status_code == 200
    assert "status" in response.json


