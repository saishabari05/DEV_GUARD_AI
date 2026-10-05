import os
import json
import logging
import re
from typing import Dict, Any, List, Optional
from ..tools.repository import search_repository, read_repository_file
from ..tools.testing import run_tests
from ..repository.detector import detect_repository_metadata

logger = logging.getLogger("devguard.autonomous")

def run_autonomous_investigation(
    repo_path: str,
    repo_identifier: str,
    metadata: Optional[Dict[str, Any]] = None,
    bug_report: Optional[str] = None
) -> Dict[str, Any]:
    """
    Executes the deterministic evidence collection pipeline before sending structured context to Gemini AI.
    """
    logs: List[str] = []

    def log_step(step_tag: str, message: str):
        formatted = f"[DEVGUARD][{step_tag}] {message}"
        logs.append(formatted)
        logger.info(formatted)
        print(formatted)

    # 1. Preservation & Project Detection
    log_step("DISCOVERY", f"Starting autonomous discovery on workspace {repo_identifier} at {repo_path}")
    
    if not metadata:
        metadata = detect_repository_metadata(repo_path)
    
    # Ensure metadata fields are filled
    repo_url = metadata.get("repository_url")
    repo_name = metadata.get("repository_name") or repo_identifier
    local_ws_path = metadata.get("local_workspace_path") or repo_path
    language = metadata.get("language", "Unknown")
    framework = metadata.get("framework", "Unknown")
    test_framework = metadata.get("test_framework", "Unknown")
    test_command = metadata.get("test_command", "Not detected")
    file_count = metadata.get("file_count", 0)

    preserved_metadata = {
        "repository_url": repo_url,
        "repository_name": repo_name,
        "local_workspace_path": local_ws_path,
        "language": language,
        "framework": framework,
        "test_framework": test_framework,
        "test_command": test_command,
        "file_count": file_count,
        "workspace_id": repo_identifier
    }

    log_step("DISCOVERY", f"Preserved Repository Metadata: name={repo_name}, url={repo_url}, language={language}, framework={framework}, test_cmd={test_command}, file_count={file_count}")

    # 2. Inspect Repository Structure
    all_files: List[str] = []
    test_files: List[str] = []
    source_files: List[str] = []
    documentation_files: List[str] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in [".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache"]]
        for file in files:
            rel_p = os.path.relpath(os.path.join(root, file), repo_path).replace("\\", "/")
            all_files.append(rel_p)
            if "test" in rel_p.lower() or "spec" in rel_p.lower():
                test_files.append(rel_p)
            elif os.path.basename(rel_p).lower() in {
                "readme.md", "workshop.md", "contributing.md", "changelog.md"
            } or rel_p.lower().endswith((".md", ".rst", ".adoc")):
                documentation_files.append(rel_p)
            elif rel_p.endswith((".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".c", ".cpp")):
                source_files.append(rel_p)

    log_step("TEST_DISCOVERY", f"Discovered {len(test_files)} test files and {len(source_files)} source files. Test command: {test_command}")

    # 3 & 4. Execute Test Command
    log_step("TEST_EXECUTION", f"Executing test command '{test_command}'...")
    test_res = run_tests(repo_path, test_command=test_command)
    
    exit_code = test_res.get("exit_code", 1)
    stdout = test_res.get("stdout", "")
    stderr = test_res.get("stderr", "")
    test_passed = test_res.get("passed", 0)
    test_failed = test_res.get("failed", 0)
    combined_test_output = (stdout + "\n" + stderr).strip()

    # 5. Capture COMPLETE Test Result & Failure Analysis
    failing_test_names: List[str] = []
    traceback_lines: List[str] = []
    traceback_output: str = ""
    candidate_paths: Dict[str, str] = {}
    assertion_message: str = ""
    assertion_details: Dict[str, str] = {}
    error_type: str = ""

    log_step("FAILURE_ANALYSIS", f"Test execution completed with exit code {exit_code}. Passed: {test_passed}, Failed: {test_failed}")

    if exit_code != 0 or test_failed > 0:
        # Extract failing test names
        # e.g., pytest FAILED tests/test_auth.py::test_login
        failed_matches = re.findall(r'FAILED\s+([^\s]+)', combined_test_output)
        for fm in failed_matches:
            fm = fm.replace("\\", "/")
            failing_test_names.append(fm)
            clean_path = fm.split("::")[0]
            candidate_paths[clean_path] = "HIGH PRIORITY: failing test file"

        # Extract tracebacks & file paths (e.g. File "app/auth.py", line 12, in login)
        tb_matches = re.findall(r'File ["\']([^"\']+)["\'], line (\d+)(?:, in ([^\s\n]+))?', combined_test_output)
        for path_match, line_num, func_name in tb_matches:
            # normalize path
            norm_p = path_match.replace("\\", "/")
            if norm_p.startswith(repo_path.replace("\\", "/")):
                norm_p = os.path.relpath(norm_p, repo_path).replace("\\", "/")
            if not norm_p.startswith("...") and not "site-packages" in norm_p and not "Python" in norm_p:
                candidate_paths[norm_p] = "HIGH PRIORITY: traceback-referenced file"
                traceback_lines.append(f"{norm_p}:{line_num} in {func_name or 'module'}")

        # Preserve the traceback itself, but keep the context bounded for the
        # LLM payload. The deterministic test result still contains full output.
        traceback_match = re.search(
            r"(?ms)(?:=+ FAILURES =+.*?)(?:(?:=+ short test summary info =+)|\Z)",
            combined_test_output,
        )
        traceback_output = (traceback_match.group(0) if traceback_match else combined_test_output)[-12000:]

        # Extract assertion messages and error types (e.g. AssertionError, KeyError, ValueError)
        err_match = re.search(r'([A-Za-z_][A-Za-z0-9_]*Error|[A-Za-z_][A-Za-z0-9_]*Exception):\s*(.*)', combined_test_output)
        if err_match:
            error_type = err_match.group(1)
            assertion_message = err_match.group(2).strip()
            log_step("FAILURE_ANALYSIS", f"Captured Error Type: {error_type} | Assertion Message: {assertion_message}")

        # Pytest commonly renders comparisons as `assert actual == expected`.
        comparison_match = re.search(
            r"(?:^|\n)\s*E\s+assert\s+(.+?)\s*==\s*(.+?)\s*(?:\n|$)",
            combined_test_output,
        )
        if comparison_match:
            assertion_details = {
                "actual": comparison_match.group(1).strip(),
                "expected": comparison_match.group(2).strip(),
            }

    # A directed report can identify a relevant file even when the test suite
    # passes or the runner cannot parse a framework-specific traceback.
    if bug_report:
        for path in re.findall(
            r"(?<![\w/])(?:[\w.-]+/)*[\w.-]+\.(?:py|js|jsx|ts|tsx|java|go|c|cpp)",
            bug_report,
        ):
            if path in all_files:
                candidate_paths[path] = "HIGH PRIORITY: bug-report-referenced file"

    for path in documentation_files:
        log_step("EVIDENCE", f"SKIPPED LOW PRIORITY DOC: {path}")

    log_step("FAILURE_ANALYSIS", f"Identified candidate paths for source inspection: {sorted(candidate_paths)}")

    # 6 & 7 & 8. Source Inspection & Repository Search
    log_step("SOURCE_INSPECTION", f"Inspecting source contents for candidate paths...")
    inspected_files: Dict[str, str] = {}

    for cand, reason in candidate_paths.items():
        res = read_repository_file(repo_path, cand)
        if res.get("success"):
            inspected_files[cand] = res.get("content", "")
            log_step("EVIDENCE", f"{reason}: {cand}")
            log_step("SOURCE_INSPECTION", f"Read source file '{cand}' ({len(res.get('content', ''))} bytes)")

    # Follow direct imports from failing tests to the implementation under
    # test. This keeps source collection focused without asking the LLM to
    # discover obvious relationships through extra tool calls.
    imported_paths: set = set()
    for test_path, content in inspected_files.items():
        if test_path not in test_files:
            continue
        for module_name in re.findall(
            r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", content, re.MULTILINE
        ):
            module_path = module_name.replace(".", "/") + ".py"
            if module_path in all_files:
                imported_paths.add(module_path)
    for imported_path in sorted(imported_paths):
        if imported_path in inspected_files:
            continue
        res = read_repository_file(repo_path, imported_path)
        if res.get("success"):
            inspected_files[imported_path] = res.get("content", "")
            candidate_paths[imported_path] = "HIGH PRIORITY: directly imported by failing test"
            log_step("EVIDENCE", f"HIGH PRIORITY: {imported_path}")
            log_step("SOURCE_INSPECTION", f"Read source file '{imported_path}' ({len(res.get('content', ''))} bytes)")

    # If candidate files list is empty or fails, read top source files
    if not inspected_files:
        for sfile in source_files[:5]:
            res = read_repository_file(repo_path, sfile)
            if res.get("success"):
                inspected_files[sfile] = res.get("content", "")
                log_step("EVIDENCE", f"MEDIUM PRIORITY: fallback source file {sfile}")

    # Perform repository search for failing symbols / error keywords if available
    search_results: List[Dict[str, Any]] = []
    search_queries = set()
    if assertion_message:
        words = [w for w in re.findall(r'\b[A-Za-z_][A-Za-z0-9_]{3,}\b', assertion_message) if w not in ["assert", "Error", "True", "False", "None"]]
        for w in words[:3]:
            search_queries.add(w)
    for ft in failing_test_names:
        sym = ft.split("::")[-1]
        if sym and not sym.startswith("test"):
            search_queries.add(sym)

    for q in list(search_queries)[:3]:
        sres = search_repository(repo_path, q)
        if sres.get("success") and sres.get("matches"):
            search_results.extend(sres["matches"][:10])
            log_step("SOURCE_INSPECTION", f"Searched query '{q}', found {len(sres['matches'])} matches")

    # 9. Structure deterministic evidence context.
    deterministic_evidence: List[Dict[str, Any]] = []
    if exit_code != 0:
        deterministic_evidence.append({
            "type": "test_failure",
            "source": test_command,
            "description": (
                f"{test_command} exited with code {exit_code}. "
                f"Failed tests: {failing_test_names or 'not parsed'}."
            )
        })
    for item in traceback_lines:
        deterministic_evidence.append({
            "type": "stack_trace",
            "source": item,
            "description": f"Traceback location captured from test execution: {item}"
        })
    for path in inspected_files:
        deterministic_evidence.append({
            "type": "source_code",
            "source": path,
            "description": "Source/test file inspected from repository evidence."
        })

    # 9. Structure Autonomous Evidence Context
    evidence_context = {
        "repository_metadata": preserved_metadata,
        "test_command": test_command,
        "test_result": {
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "passed": test_passed,
            "failed": test_failed,
            "failing_tests": failing_test_names,
            "traceback": traceback_lines,
            "traceback_output": traceback_output,
            "assertion_message": assertion_message,
            "assertion_details": assertion_details,
            "assertion_failure": assertion_message or None,
            "actual_value": assertion_details.get("actual"),
            "expected_value": assertion_details.get("expected"),
            "error_type": error_type
        },
        "source_code_inspected": inspected_files,
        "evidence_priority": {
            "high": list(candidate_paths.keys()),
            "medium": [],
            "low_skipped": documentation_files,
        },
        "evidence_budget": {
            "deterministic_files_read": len(inspected_files),
            "duplicate_reads_avoided": True,
            "documentation_reads": 0,
        },
        "repository_search_results": search_results,
        "existing_files_in_repo": all_files,
        "deterministic_evidence": deterministic_evidence
    }

    log_step("GEMINI_ANALYSIS", f"Evidence collection complete. Preparing Gemini payload with {len(inspected_files)} source files.")
    return {
        "metadata": preserved_metadata,
        "evidence_context": evidence_context,
        "logs": logs
    }
