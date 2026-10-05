import os
from typing import Dict, Any
from ..tools.testing import run_tests
from ..tools.patching import apply_patch, revert_patch
from ..tools.git import get_git_diff

def validate_patch(repo_path: str, proposed_patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a patch by executing tests before applying, applying patch, executing tests after applying,
    and returning precise evidence-backed status transitions.
    """
    if not proposed_patch or not isinstance(proposed_patch, dict):
        return {
            "success": False,
            "status": "PATCH_FAILED",
            "error": "No patch available to validate",
            "pre_test": None,
            "post_test": None
        }

    file_path = proposed_patch.get("file")
    new_content = proposed_patch.get("patch")
    
    if not file_path or not isinstance(file_path, str):
        return {
            "success": False,
            "status": "PATCH_FAILED",
            "error": "Missing or invalid 'file' in proposed patch",
            "pre_test": None,
            "post_test": None
        }
        
    if not new_content or not isinstance(new_content, str):
        return {
            "success": False,
            "status": "PATCH_FAILED",
            "error": "Missing or invalid 'patch' in proposed patch",
            "pre_test": None,
            "post_test": None
        }
        
    if os.path.isabs(file_path) or ".." in file_path:
        return {
            "success": False,
            "status": "PATCH_FAILED",
            "error": "Patch path must be relative to repository",
            "pre_test": None,
            "post_test": None
        }
        
    # 1. Pre-patch test execution (BEFORE_FIX)
    pre_test = run_tests(repo_path)
    
    # 2. Apply patch (PATCH_APPLIED)
    patch_res = apply_patch(repo_path, file_path, new_content)
    if not patch_res.get("success"):
        return {
            "success": False,
            "status": "PATCH_APPLICATION_FAILED",
            "error": patch_res.get("error", "Failed to apply patch"),
            "pre_test": pre_test,
            "post_test": None
        }
        
    patch_info = {
        "success": True,
        "status": "PATCH_APPLIED",
        "files_changed": [file_path]
    }
        
    # 3. Get git diff
    diff_res = get_git_diff(repo_path)
    actual_diff = diff_res.get("diff", "")
    
    # 4. Post-patch test execution (VALIDATING -> PASSED / FAILED)
    post_test = run_tests(repo_path)
    
    if post_test.get("success") and post_test.get("exit_code") == 0:
        return {
            "success": True,
            "status": "VALIDATED",
            "pre_test": pre_test,
            "post_test": post_test,
            "diff": actual_diff,
            "patch_result": patch_info
        }
    else:
        # Revert patch if post-test failed
        revert_patch(repo_path, file_path)
        reverted_diff_res = get_git_diff(repo_path)
        
        return {
            "success": False,
            "status": "VALIDATION_FAILED",
            "pre_test": pre_test,
            "post_test": post_test,
            "diff": actual_diff,
            "reverted_diff": reverted_diff_res.get("diff", ""),
            "patch_result": patch_info,
            "reason": post_test.get("error") or "Tests failed after patch"
        }

