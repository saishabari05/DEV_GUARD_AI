import os
from typing import Dict, Any, List
from . import resolve_safe_path

def search_repository(repository_path: str, query: str) -> Dict[str, Any]:
    try:
        repo_root = os.path.abspath(repository_path)
        if not os.path.isdir(repo_root):
            return {"success": False, "error": f"Repository not found: {repository_path}"}
            
        matches = []
        for root, _, files in os.walk(repo_root):
            # Skip hidden dirs and common non-source directories
            if "/." in root.replace('\\', '/') or "\\." in root or "__pycache__" in root or "venv" in root:
                continue
            for file in files:
                if file.startswith('.'):
                    continue
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        for idx, line in enumerate(lines):
                            if query in line:
                                rel_path = os.path.relpath(file_path, repo_root)
                                rel_path = rel_path.replace('\\', '/')
                                matches.append({
                                    "file": rel_path,
                                    "line": idx + 1,
                                    "content": line.strip()
                                })
                except (UnicodeDecodeError, IOError):
                    pass # Skip binary or unreadable files
        return {
            "success": True,
            "query": query,
            "matches": matches,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def read_repository_file(repository_path: str, file_path: str) -> Dict[str, Any]:
    try:
        safe_path = resolve_safe_path(repository_path, file_path)
        if not os.path.isfile(safe_path):
            return {
                "success": False,
                "error": f"File not found: {file_path}"
            }
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {
            "success": True,
            "path": file_path,
            "content": content,
            "error": None
        }
    except ValueError as ve:
        return {
            "success": False,
            "error": str(ve)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
