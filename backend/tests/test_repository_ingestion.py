import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.repository.workspace import create_workspace, resolve_workspace_path, extract_zip_repository, clone_git_repository
from app.repository.detector import detect_repository_metadata
from app.repository.manager import RepositoryManager

def test_workspace_creation_and_resolution():
    ws_id, ws_path = create_workspace()
    assert ws_id.startswith("ws_")
    resolved = resolve_workspace_path(ws_id)
    assert os.path.abspath(ws_path) == os.path.abspath(resolved)

def test_reject_workspace_path_traversal():
    with pytest.raises(ValueError, match="Invalid characters"):
        resolve_workspace_path("../auth_bug")

def test_invalid_git_urls():
    with pytest.raises(ValueError):
        clone_git_repository("ftp://example.com/repo.git")

def test_detector_python_flask():
    ws_id, ws_path = create_workspace()
    with open(os.path.join(ws_path, "requirements.txt"), "w") as f:
        f.write("flask==3.0.0\npytest==8.0.0\n")
    with open(os.path.join(ws_path, "app.py"), "w") as f:
        f.write("from flask import Flask\napp = Flask(__name__)\n")
    meta = detect_repository_metadata(ws_path)
    assert meta["language"] == "Python"
    assert meta["framework"] == "Flask"
    assert meta["test_command"] == "pytest"
    assert meta["file_count"] > 0

def test_detector_python_db():
    ws_id, ws_path = create_workspace()
    with open(os.path.join(ws_path, "pytest.ini"), "w") as f:
        f.write("[pytest]\n")
    with open(os.path.join(ws_path, "test_db.py"), "w") as f:
        f.write("def test_db(): pass\n")
    meta = detect_repository_metadata(ws_path)
    assert meta["language"] == "Python"
    assert meta["test_command"] == "pytest"


def test_zip_packaging_and_ingestion():
    import io, zipfile
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("app/__init__.py", "# init")
        zf.writestr("app/auth.py", "def authenticate(): pass")
        zf.writestr(".env", "SECRET_KEY=12345")
    
    zip_bytes = zip_buf.getvalue()
    ingest_res = RepositoryManager.ingest_zip_repo(zip_bytes)
    assert "workspace_id" in ingest_res
    ws_id = ingest_res["workspace_id"]
    
    fixed_zip = RepositoryManager.package_fixed_repo(ws_id)
    assert len(fixed_zip) > 0
    with zipfile.ZipFile(io.BytesIO(fixed_zip)) as zf:
        names = zf.namelist()
        assert "app/auth.py" in names
        assert ".env" not in names # Excluded secret files check
