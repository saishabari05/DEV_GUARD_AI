import os
import shutil
import zipfile
import subprocess
import uuid
import re
from typing import Dict, Any, Optional

WORKSPACES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "workspaces"))

def ensure_workspaces_dir():
    os.makedirs(WORKSPACES_DIR, exist_ok=True)

def create_workspace() -> str:
    """Creates a unique isolated workspace directory."""
    ensure_workspaces_dir()
    workspace_id = f"ws_{uuid.uuid4().hex[:10]}"
    workspace_path = os.path.join(WORKSPACES_DIR, workspace_id)
    os.makedirs(workspace_path, exist_ok=True)
    return workspace_id, workspace_path

def resolve_workspace_path(workspace_id: str) -> str:
    """Safely resolves workspace path ensuring workspace isolation."""
    ensure_workspaces_dir()
    if not workspace_id or not isinstance(workspace_id, str):
        raise ValueError("Invalid workspace ID.")
    if ".." in workspace_id or "/" in workspace_id or "\\" in workspace_id:
        raise ValueError("Invalid characters in workspace ID.")

    path = os.path.abspath(os.path.join(WORKSPACES_DIR, workspace_id))
    if os.path.commonpath([path, WORKSPACES_DIR]) != WORKSPACES_DIR:
        raise ValueError("Workspace path traversal detected.")
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Workspace directory not found: {workspace_id}")
    return path

def clone_git_repository(git_url: str) -> tuple:
    """Clones a public HTTPS Git repository into an isolated workspace."""
    git_url = git_url.strip()
    # Validate URL format
    if not (git_url.startswith("https://") or git_url.startswith("http://")):
        raise ValueError("Only HTTP/HTTPS Git URLs are supported.")
    if not (git_url.endswith(".git") or "github.com/" in git_url or "gitlab.com/" in git_url or "bitbucket.org/" in git_url):
        raise ValueError("Invalid Git repository URL.")

    workspace_id, workspace_path = create_workspace()

    try:
        cmd = ["git", "clone", "--depth", "1", git_url, workspace_path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            shutil.rmtree(workspace_path, ignore_errors=True)
            raise RuntimeError(f"Git clone failed: {result.stderr or result.stdout}")
        return workspace_id, workspace_path
    except Exception as e:
        shutil.rmtree(workspace_path, ignore_errors=True)
        raise RuntimeError(f"Failed to clone repository: {str(e)}")

def extract_zip_repository(zip_file_bytes: bytes) -> tuple:
    """Extracts uploaded repository ZIP file into an isolated workspace safely."""
    workspace_id, workspace_path = create_workspace()
    temp_zip = os.path.join(workspace_path, "upload.zip")

    try:
        with open(temp_zip, "wb") as f:
            f.write(zip_file_bytes)

        with zipfile.ZipFile(temp_zip, "r") as zf:
            for member in zf.infolist():
                # Security check: path traversal and absolute paths
                target_path = os.path.abspath(os.path.join(workspace_path, member.filename))
                if os.path.commonpath([target_path, workspace_path]) != workspace_path:
                    raise ValueError(f"Malicious archive entry detected: {member.filename}")
                if member.is_dir():
                    os.makedirs(target_path, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(target_path), exist_ok=True)
                    with zf.open(member) as source, open(target_path, "wb") as target:
                        shutil.copyfileobj(source, target)

        os.remove(temp_zip)

        # Handle top-level single folder extraction pattern (common in Github zip exports)
        items = os.listdir(workspace_path)
        if len(items) == 1 and os.path.isdir(os.path.join(workspace_path, items[0])):
            single_folder = os.path.join(workspace_path, items[0])
            for sub_item in os.listdir(single_folder):
                shutil.move(os.path.join(single_folder, sub_item), workspace_path)
            os.rmdir(single_folder)

        return workspace_id, workspace_path
    except Exception as e:
        shutil.rmtree(workspace_path, ignore_errors=True)
        raise RuntimeError(f"ZIP extraction failed: {str(e)}")

def create_repository_zip(workspace_path: str) -> bytes:
    """Packages the fixed repository into an in-memory ZIP buffer, excluding secret files."""
    workspace_path = os.path.abspath(workspace_path)
    import io

    zip_buffer = io.BytesIO()
    excl_files = [".env", ".env.local", ".git", "__pycache__", ".pytest_cache", "venv", ".venv", "node_modules"]

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(workspace_path):
            dirs[:] = [d for d in dirs if d not in excl_files]
            for file in files:
                if file in [".env", ".env.local", "id_rsa", "id_ed25519"]:
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, workspace_path)
                zf.write(file_path, rel_path)

    zip_buffer.seek(0)
    return zip_buffer.getvalue()

def clean_workspace(workspace_id: str):
    """Safely removes an isolated workspace directory."""
    try:
        path = resolve_workspace_path(workspace_id)
        shutil.rmtree(path, ignore_errors=True)
    except Exception:
        pass
