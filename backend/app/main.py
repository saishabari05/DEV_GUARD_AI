import os
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.exceptions import BadRequest, NotFound, InternalServerError
import io

from .tools.repository import search_repository
from .tools.testing import run_tests
from .tools.patching import apply_patch, revert_patch
from .tools.git import get_git_diff
from .agent.investigator import investigate
from .agent.validator import validate_patch
from .agent.report_generator import generate_report
from .repository.manager import RepositoryManager
from .repository.workspace import resolve_workspace_path

api_bp = Blueprint('api', __name__)

def resolve_target_path(repo_identifier: str) -> str:

    """
    Resolves repository path strictly from an ingested workspace_id (e.g. ws_xxx).
    """
    if not repo_identifier or not isinstance(repo_identifier, str):
        raise BadRequest("Invalid or missing repository identifier")

    if not repo_identifier.startswith("ws_"):
        raise BadRequest("Repository identifier must be a valid workspace ID (ws_...)")

    try:
        return resolve_workspace_path(repo_identifier)
    except ValueError as ve:
        raise BadRequest(str(ve))
    except FileNotFoundError as fnf:
        raise NotFound(str(fnf))


@api_bp.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "service": "devguard-backend"
    })

@api_bp.route('/repositories/import', methods=['POST'])
def import_git_repo():
    data = request.get_json()
    if not data or not data.get("git_url"):
        raise BadRequest("Missing 'git_url' in request body")
    try:
        res = RepositoryManager.ingest_git_repo(data["git_url"])
        return jsonify({"success": True, **res})
    except Exception as e:
        raise BadRequest(str(e))

@api_bp.route('/repositories/upload', methods=['POST'])
def upload_zip_repo():
    if 'file' not in request.files:
        raise BadRequest("Missing 'file' field in multipart request")
    file = request.files['file']
    if not file.filename.endswith('.zip'):
        raise BadRequest("Uploaded file must be a .zip file")
    try:
        zip_bytes = file.read()
        res = RepositoryManager.ingest_zip_repo(zip_bytes)
        return jsonify({"success": True, **res})
    except Exception as e:
        raise BadRequest(str(e))

@api_bp.route('/repositories/<repo_id>/metadata', methods=['GET'])
def get_repo_metadata(repo_id):
    try:
        metadata = RepositoryManager.get_metadata(repo_id)
        return jsonify({"success": True, "metadata": metadata})
    except Exception as e:
        raise NotFound(str(e))

@api_bp.route('/investigate', methods=['POST'])
def investigate_route():
    data = request.get_json()
    if not data:
        raise BadRequest("Missing JSON body")
        
    repo_identifier = data.get("repository")
    bug_report = data.get("bug_report")
    require_approval = data.get("require_approval", True)
    mode = data.get("mode") # 'autonomous' or 'directed'
    
    if mode == "directed" and (not bug_report or not isinstance(bug_report, str)):
        raise BadRequest("Missing or invalid bug_report for Directed Investigation mode")
        
    repo_path = resolve_target_path(repo_identifier)
    
    result = investigate(repo_path, repo_identifier, bug_report if mode == "directed" else None)
    
    # Run pre-test validation check if patch was proposed
    proposed_patch = result.get("proposed_patch") or (
        {"file": result.get("affected_file"), "patch": result.get("patch")} 
        if result.get("patch") and result.get("affected_file") else None
    )

    if result.get("status") == "PROVIDER_ERROR":
        # Surface real Gemini/API failures instead of disguising them as an
        # evidence problem.
        result["report_markdown"] = generate_report(result)
        return jsonify(result), 502

    if proposed_patch:
        diff_res = get_git_diff(repo_path)
        result["diff_preview"] = diff_res.get("diff", "")
        
        if not require_approval:
            validation_result = validate_patch(repo_path, proposed_patch)
            result["validation_pipeline"] = validation_result
            if validation_result.get("success"):
                result["status"] = "PASSED"
            else:
                result["status"] = "FAILED"
        else:
            result["status"] = "AWAITING_APPROVAL"
    else:
        if result.get("confidence") == "INSUFFICIENT":
            result["status"] = "INSUFFICIENT_EVIDENCE"
        elif not proposed_patch:
            result["status"] = "PATCH_NOT_AVAILABLE"

    result["report_markdown"] = generate_report(result)
    return jsonify(result)

@api_bp.route('/fix/approve', methods=['POST'])
def approve_fix_route():
    data = request.get_json()
    if not data or not data.get("repository") or not data.get("proposed_patch"):
        raise BadRequest("Missing repository or proposed_patch in request")

    repo_identifier = data.get("repository")
    proposed_patch = data.get("proposed_patch")
    repo_path = resolve_target_path(repo_identifier)

    val_res = validate_patch(repo_path, proposed_patch)
    status = "PASSED" if val_res.get("success") else "FAILED"

    return jsonify({
        "success": val_res.get("success", False),
        "status": status,
        "validation_pipeline": val_res
    })


@api_bp.route('/investigations/<repo_id>/patch', methods=['GET'])
def download_patch(repo_id):
    repo_path = resolve_target_path(repo_id)
    diff_res = get_git_diff(repo_path)
    patch_content = diff_res.get("diff", "")
    
    if not patch_content:
        # Fallback patch header if clean
        patch_content = "# No active git diff modifications found.\n"

    buf = io.BytesIO(patch_content.encode('utf-8'))
    return send_file(
        buf,
        mimetype="text/plain",
        as_attachment=True,
        download_name=f"devguard-fix-{repo_id}.patch"
    )

@api_bp.route('/investigations/<repo_id>/download', methods=['GET'])
def download_fixed_repository(repo_id):
    repo_path = resolve_target_path(repo_id)
    try:
        zip_bytes = RepositoryManager.package_fixed_repo(repo_id) if repo_id.startswith("ws_") else create_repo_zip_direct(repo_path)
        buf = io.BytesIO(zip_bytes)
        return send_file(
            buf,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"devguard-fixed-{repo_id}.zip"
        )
    except Exception as e:
        raise InternalServerError(f"Failed to generate repository zip: {str(e)}")

def create_repo_zip_direct(repo_path: str) -> bytes:
    from .repository.workspace import create_repository_zip
    return create_repository_zip(repo_path)

@api_bp.route('/tools/search', methods=['POST'])
def tools_search():
    data = request.get_json()
    if not data:
        raise BadRequest("Missing JSON body")
    repo_identifier = data.get("repository")
    query = data.get("query")
    if not query or not isinstance(query, str):
        raise BadRequest("Missing or invalid query")
    repo_path = resolve_target_path(repo_identifier)
    return jsonify(search_repository(repo_path, query))

@api_bp.route('/tools/test', methods=['POST'])
def tools_test():
    data = request.get_json()
    if not data:
        raise BadRequest("Missing JSON body")
    repo_identifier = data.get("repository")
    repo_path = resolve_target_path(repo_identifier)
    return jsonify(run_tests(repo_path))

@api_bp.route('/tools/apply', methods=['POST'])
def tools_apply():
    data = request.get_json()
    if not data:
        raise BadRequest("Missing JSON body")
    repo_identifier = data.get("repository")
    file_path = data.get("file_path")
    patch = data.get("patch")
    if not file_path or not patch:
        raise BadRequest("Missing file_path or patch")
    repo_path = resolve_target_path(repo_identifier)
    return jsonify(apply_patch(repo_path, file_path, patch))

@api_bp.route('/tools/revert', methods=['POST'])
def tools_revert():
    data = request.get_json()
    if not data:
        raise BadRequest("Missing JSON body")
    repo_identifier = data.get("repository")
    file_path = data.get("file_path")
    if not file_path:
        raise BadRequest("Missing file_path")
    repo_path = resolve_target_path(repo_identifier)
    return jsonify(revert_patch(repo_path, file_path))
