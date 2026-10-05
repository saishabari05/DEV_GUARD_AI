import os
import re
import subprocess
import sys
import time
from typing import Dict, Any, Optional

def run_tests(
    repository_path: str,
    test_command: Optional[str] = None,
    timeout_seconds: int = 120,
) -> Dict[str, Any]:
    """Run the detected test command inside an isolated repository workspace.

    The complete stdout/stderr and exit code are preserved because failed tests are
    evidence for the investigation agent, not merely a boolean success/failure.
    """
    repo_root = os.path.abspath(repository_path)
    if not os.path.isdir(repo_root):
        return {
            "success": False, "status": "failed",
            "command": test_command or "Not detected", "exit_code": 1,
            "stdout": "", "stderr": f"Repository directory not found: {repository_path}",
            "duration_seconds": 0.0, "passed": 0, "failed": 0,
            "error": "Directory not found",
        }

    if not test_command or test_command in {"Not detected", "Unknown"}:
        from ..repository.detector import detect_repository_metadata
        test_command = detect_repository_metadata(repo_root).get("test_command", "Not detected")

    if test_command == "Not detected":
        return {
            "success": False, "status": "not_detected",
            "command": "Not detected", "exit_code": 1,
            "stdout": "", "stderr": "No test command detected in workspace",
            "duration_seconds": 0.0, "passed": 0, "failed": 0,
            "error": "No test command detected",
        }

    # Prefer a repository-local pytest executable when one exists; otherwise use
    # the current Python interpreter so DEVGUARD can run external Python repos.
    if test_command.strip() == "pytest":
        candidates = [
            os.path.join(repo_root, "venv", "Scripts", "pytest.exe"),
            os.path.join(repo_root, ".venv", "Scripts", "pytest.exe"),
            os.path.join(repo_root, "venv", "bin", "pytest"),
            os.path.join(repo_root, ".venv", "bin", "pytest"),
        ]
        local_pytest = next((p for p in candidates if os.path.isfile(p)), None)
        cmd_list = [local_pytest] if local_pytest else [sys.executable, "-m", "pytest"]
    else:
        cmd_list = test_command.split()

    start_time = time.time()
    try:
        result = subprocess.run(
            cmd_list,
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            shell=False,
        )
        duration = round(time.time() - start_time, 2)
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        exit_code = result.returncode

        passed_match = re.search(r"(\d+)\s+passed", stdout + "\n" + stderr)
        failed_match = re.search(r"(\d+)\s+failed", stdout + "\n" + stderr)
        passed = int(passed_match.group(1)) if passed_match else 0
        failed = int(failed_match.group(1)) if failed_match else 0

        return {
            "success": exit_code == 0,
            "status": "passed" if exit_code == 0 else "failed",
            "command": test_command,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_seconds": duration,
            "passed": passed,
            "failed": failed,
            "error": None if exit_code == 0 else (stderr.strip() or f"Tests failed with exit code {exit_code}"),
        }
    except subprocess.TimeoutExpired as exc:
        duration = round(time.time() - start_time, 2)
        stdout = exc.stdout or ""
        stderr = exc.stderr or f"Test execution timed out after {timeout_seconds} seconds"
        return {
            "success": False, "status": "timeout", "command": test_command,
            "exit_code": 124, "stdout": stdout, "stderr": stderr,
            "duration_seconds": duration, "passed": 0, "failed": 0,
            "error": "Test execution timed out",
        }
    except FileNotFoundError:
        duration = round(time.time() - start_time, 2)
        return {
            "success": False, "status": "command_not_found", "command": test_command,
            "exit_code": 127, "stdout": "",
            "stderr": f"Command not found: {test_command}",
            "duration_seconds": duration, "passed": 0, "failed": 0,
            "error": f"Command not found: {test_command}",
        }
    except Exception as exc:
        duration = round(time.time() - start_time, 2)
        return {
            "success": False, "status": "error", "command": test_command,
            "exit_code": 1, "stdout": "", "stderr": str(exc),
            "duration_seconds": duration, "passed": 0, "failed": 0,
            "error": str(exc),
        }
