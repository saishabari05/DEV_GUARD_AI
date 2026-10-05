import os
from pathlib import Path

def resolve_safe_path(repository_path: str, target_path: str) -> str:
    """
    Resolves a target path safely within the repository path.
    Raises ValueError if path traversal is detected.
    """
    repo_root = Path(repository_path).resolve()
    target = (repo_root / target_path).resolve()
    
    # Check if target is relative to repo_root
    try:
        target.relative_to(repo_root)
    except ValueError:
        raise ValueError(f"Path traversal detected: {target_path} escapes {repository_path}")
        
    return str(target)
