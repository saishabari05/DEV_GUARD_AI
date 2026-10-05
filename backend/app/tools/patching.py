import os
import shutil
from typing import Dict, Any
from . import resolve_safe_path

def apply_patch(repository_path: str, file_path: str, new_content: str) -> Dict[str, Any]:
    try:
        safe_path = resolve_safe_path(repository_path, file_path)
        if not os.path.isfile(safe_path):
             return {
                 "success": False,
                 "error": f"File not found: {file_path}"
             }
             
        backup_path = safe_path + ".bak"
        # Create backup if it doesn't exist for this session
        if not os.path.exists(backup_path):
            shutil.copy2(safe_path, backup_path)
        
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        return {
            "success": True,
            "message": "Patch applied successfully",
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

def revert_patch(repository_path: str, file_path: str) -> Dict[str, Any]:
    try:
        safe_path = resolve_safe_path(repository_path, file_path)
        backup_path = safe_path + ".bak"
        
        if not os.path.isfile(backup_path):
            return {
                 "success": False,
                 "error": f"No backup found for {file_path}"
            }
            
        shutil.copy2(backup_path, safe_path)
        os.remove(backup_path)
        
        return {
            "success": True,
            "message": "Patch reverted successfully",
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
