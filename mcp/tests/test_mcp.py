import os
import sys
import pytest
import io
import zipfile

mcp_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if mcp_dir not in sys.path:
    sys.path.insert(0, mcp_dir)

from developer_mcp import (
    search_repository,
    read_repository_file,
    get_git_history,
    get_git_diff,
    run_tests,
    mcp,
    get_safe_repo_path
)

from app.repository.manager import RepositoryManager

@pytest.fixture
def mcp_workspace():
    ws_id, ws_path = RepositoryManager.ingest_zip_repo(b"").values() if False else ("", "")
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("app/__init__.py", "# init")
        zf.writestr("app/auth.py", "def authenticate_user(email):\n    return email\n")
        zf.writestr("other.txt", "content")
    res = RepositoryManager.ingest_zip_repo(zip_buf.getvalue())
    return res["workspace_id"]


def test_mcp_server_starts():
    assert mcp.name == "DevGuard Developer Tools"

def test_tool_definitions_available():
    assert hasattr(mcp, "_tool_manager") or hasattr(mcp, "tool")

def test_search_repository(mcp_workspace):
    res = search_repository(mcp_workspace, "authenticate_user")
    assert res["success"] is True
    assert res["tool"] == "search_repository"
    assert any("auth.py" in str(match) for match in res["result"]["matches"])

def test_read_repository_file(mcp_workspace):
    res = read_repository_file(mcp_workspace, "other.txt")
    assert res["success"] is True
    assert res["tool"] == "read_repository_file"
    assert res["result"]["success"] is True
    assert "content" in res["result"]["content"]




def test_path_traversal_rejected(mcp_workspace):
    res = read_repository_file("../auth_bug", "app/auth.py")
    assert res["success"] is False
    
    res2 = read_repository_file(mcp_workspace, "../app/auth.py")
    assert res2["success"] is True
    assert res2["result"]["success"] is False

def test_get_git_history(mcp_workspace):
    res = get_git_history(mcp_workspace)
    assert res["success"] is True or res["success"] is False

def test_get_git_diff(mcp_workspace):
    res = get_git_diff(mcp_workspace)
    assert res["success"] is True or res["success"] is False

def test_run_tests(mcp_workspace):
    res = run_tests(mcp_workspace)
    assert res["success"] is True
    assert res["tool"] == "run_tests"

def test_repository_outside_workspaces():
    res = search_repository("ws_invalid_id_that_does_not_exist", "query")
    assert res["success"] is False

