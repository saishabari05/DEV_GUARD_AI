import os
import sys

mcp_root_dir = os.path.abspath(os.path.dirname(__file__))
if mcp_root_dir not in sys.path:
    sys.path.insert(0, mcp_root_dir)

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from server.mcpserver import MCPServer
from app.tools.repository import search_repository as _search_repository
from app.tools.repository import read_repository_file as _read_repository_file
from app.tools.git import get_git_history as _get_git_history, get_git_diff as _get_git_diff
from app.tools.testing import run_tests as _run_tests

from app.repository.workspace import resolve_workspace_path

def get_safe_repo_path(repository: str) -> str:
    """Validates and resolves the repository path securely using workspace IDs."""
    if not repository or not isinstance(repository, str):
        raise ValueError("Invalid repository name")
    if not repository.startswith("ws_"):
        raise ValueError("Repository identifier must be a valid workspace ID (ws_...)")
        
    return resolve_workspace_path(repository)


mcp = MCPServer("DevGuard Developer Tools")

@mcp.tool()
def search_repository(repository: str, query: str) -> dict:
    """Search the repository for a given text query."""
    print(f"[MCP] Tool requested: search_repository", file=sys.stderr)
    print(f"[MCP] Repository: {repository}", file=sys.stderr)
    try:
        repo_path = get_safe_repo_path(repository)
        res = _search_repository(repo_path, query)
        print("[MCP] Tool completed", file=sys.stderr)
        return {"success": True, "tool": "search_repository", "result": res, "error": None}
    except Exception as e:
        print(f"[MCP] Tool error: {e}", file=sys.stderr)
        return {"success": False, "tool": "search_repository", "result": None, "error": str(e)}

@mcp.tool()
def read_repository_file(repository: str, file_path: str) -> dict:
    """Read a file from the repository."""
    print(f"[MCP] Tool requested: read_repository_file", file=sys.stderr)
    print(f"[MCP] Repository: {repository}", file=sys.stderr)
    try:
        repo_path = get_safe_repo_path(repository)
        res = _read_repository_file(repo_path, file_path)
        print("[MCP] Tool completed", file=sys.stderr)
        return {"success": True, "tool": "read_repository_file", "result": res, "error": None}
    except Exception as e:
        print(f"[MCP] Tool error: {e}", file=sys.stderr)
        return {"success": False, "tool": "read_repository_file", "result": None, "error": str(e)}

@mcp.tool()
def get_git_history(repository: str) -> dict:
    """Get the git commit history of the repository."""
    print(f"[MCP] Tool requested: get_git_history", file=sys.stderr)
    print(f"[MCP] Repository: {repository}", file=sys.stderr)
    try:
        repo_path = get_safe_repo_path(repository)
        res = _get_git_history(repo_path)
        print("[MCP] Tool completed", file=sys.stderr)
        return {"success": True, "tool": "get_git_history", "result": res, "error": None}
    except Exception as e:
        print(f"[MCP] Tool error: {e}", file=sys.stderr)
        return {"success": False, "tool": "get_git_history", "result": None, "error": str(e)}

@mcp.tool()
def get_git_diff(repository: str) -> dict:
    """Get the git diff of the repository."""
    print(f"[MCP] Tool requested: get_git_diff", file=sys.stderr)
    print(f"[MCP] Repository: {repository}", file=sys.stderr)
    try:
        repo_path = get_safe_repo_path(repository)
        res = _get_git_diff(repo_path)
        print("[MCP] Tool completed", file=sys.stderr)
        return {"success": True, "tool": "get_git_diff", "result": res, "error": None}
    except Exception as e:
        print(f"[MCP] Tool error: {e}", file=sys.stderr)
        return {"success": False, "tool": "get_git_diff", "result": None, "error": str(e)}

@mcp.tool()
def run_tests(repository: str) -> dict:
    """Execute pytest in the repository."""
    print(f"[MCP] Tool requested: run_tests", file=sys.stderr)
    print(f"[MCP] Repository: {repository}", file=sys.stderr)
    try:
        repo_path = get_safe_repo_path(repository)
        res = _run_tests(repo_path)
        print("[MCP] Tool completed", file=sys.stderr)
        return {"success": True, "tool": "run_tests", "result": res, "error": None}
    except Exception as e:
        print(f"[MCP] Tool error: {e}", file=sys.stderr)
        return {"success": False, "tool": "run_tests", "result": None, "error": str(e)}

if __name__ == "__main__":
    print("[MCP] Server starting", file=sys.stderr)
    mcp.run(transport='stdio')
