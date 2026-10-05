import subprocess
import os
from typing import Dict, Any

def get_git_history(repository_path: str) -> Dict[str, Any]:
    try:
        repo_root = os.path.abspath(repository_path)
        if not os.path.isdir(os.path.join(repo_root, ".git")):
            return {
                "success": False,
                "error": "Repository is not a Git repository"
            }
            
        result = subprocess.run(
            ["git", "log", "-n", "5", "--pretty=format:%H|%an|%ad|%s", "--date=short"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        history = []
        for line in result.stdout.split('\n'):
            if not line.strip(): continue
            parts = line.split('|', 3)
            if len(parts) == 4:
                history.append({
                    "hash": parts[0],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })
        return {
            "success": True,
            "history": history,
            "error": None
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": e.stderr.strip() or str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

def get_git_diff(repository_path: str) -> Dict[str, Any]:
    try:
        repo_root = os.path.abspath(repository_path)
        if not os.path.isdir(os.path.join(repo_root, ".git")):
            return {
                "success": False,
                "error": "Repository is not a Git repository"
            }
            
        result = subprocess.run(
            ["git", "diff"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True
        )
        return {
            "success": True,
            "diff": result.stdout,
            "error": None
        }
    except subprocess.CalledProcessError as e:
        return {
            "success": False,
            "error": e.stderr.strip() or str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
