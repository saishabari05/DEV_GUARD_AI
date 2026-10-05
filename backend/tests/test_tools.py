import os
import pytest
import io
import zipfile
from app.tools.repository import search_repository, read_repository_file
from app.tools.git import get_git_history, get_git_diff
from app.tools.testing import run_tests
from app.tools.patching import apply_patch, revert_patch
from app.repository.workspace import create_workspace

@pytest.fixture
def workspace_dir():
    ws_id, ws_path = create_workspace()
    with open(os.path.join(ws_path, "README.md"), "w") as f:
        f.write("# Sample Repo\n")
    os.makedirs(os.path.join(ws_path, "app"), exist_ok=True)
    with open(os.path.join(ws_path, "app", "auth.py"), "w") as f:
        f.write("def authenticate_user(user):\n    return True\n")
    return ws_path

def test_search_repository(workspace_dir):
    res = search_repository(workspace_dir, "authenticate_user")
    assert res["success"] is True
    files = [m["file"] for m in res["matches"]]
    assert "app/auth.py" in files

def test_read_repository_file(workspace_dir):
    res = read_repository_file(workspace_dir, "app/auth.py")
    assert res["success"] is True
    assert "def authenticate_user" in res["content"]

def test_path_traversal_protection(workspace_dir):
    res = read_repository_file(workspace_dir, "../../README.md")
    assert res["success"] is False
    assert "escapes" in res["error"].lower() or "traversal" in res["error"].lower()

def test_git_tools_no_git(workspace_dir):
    res_history = get_git_history(workspace_dir)
    assert res_history["success"] is False
    assert "not a git repository" in res_history["error"].lower()

    res_diff = get_git_diff(workspace_dir)
    assert res_diff["success"] is False
    assert "not a git repository" in res_diff["error"].lower()

def test_run_tests(workspace_dir):
    res = run_tests(workspace_dir)
    assert "status" in res

def test_patching(workspace_dir):
    res_read_orig = read_repository_file(workspace_dir, "README.md")
    orig_content = res_read_orig["content"]
    
    new_content = orig_content + "\n# PATCHED\n"
    res_patch = apply_patch(workspace_dir, "README.md", new_content)
    assert res_patch["success"] is True
    
    res_read_patched = read_repository_file(workspace_dir, "README.md")
    assert "PATCHED" in res_read_patched["content"]
    
    res_revert = revert_patch(workspace_dir, "README.md")
    assert res_revert["success"] is True
    
    res_read_reverted = read_repository_file(workspace_dir, "README.md")
    assert "PATCHED" not in res_read_reverted["content"]

