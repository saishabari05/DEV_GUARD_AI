import re
from typing import Dict, Any, List, Callable
from .base import LLMProvider

class MockProvider(LLMProvider):
    def investigate(self, repo_path: str, repo_name: str, bug_report: str, tools: List[Callable]) -> Dict[str, Any]:
        tool_map = {t.__name__: t for t in tools}
        tool_log = []
        
        def call_tool(name: str, **kwargs):
            tool_log.append(f"Mock requested: {name} with {kwargs}")
            if name in tool_map:
                res = tool_map[name](**kwargs)
                tool_log.append(f"Tool result: {str(res)[:500]}")
                return res
            else:
                tool_log.append(f"Tool result: Error unknown tool")
                return {"success": False, "error": "Unknown tool"}
            
        print(f"[DEVGUARD] Mock investigation started for {repo_name}")
        
        res_test = call_tool("tool_run_tests")
        
        evidence = []
        parsed_file = None
        parsed_func = None

        if isinstance(res_test, dict) and res_test.get("exit_code", 0) != 0:
            stdout = res_test.get("stdout", "")
            stderr = res_test.get("stderr", "")
            combined_output = stdout + "\n" + stderr

            # Extract failing test name / file from pytest output
            fail_match = re.search(r'FAILED\s+([^\s:]+)(?:::([^\s]+))?', combined_output)
            if fail_match:
                test_file = fail_match.group(1)
                test_func = fail_match.group(2) or "test"
                evidence.append({
                    "type": "test_failure",
                    "source": test_file,
                    "description": f"Test failure detected in {test_file} ({test_func})"
                })
                parsed_file = test_file
                parsed_func = test_func

            # Extract traceback file reference
            tb_match = re.search(r'File "([^"]+)", line (\d+), in ([^\s]+)', combined_output)
            if tb_match:
                tb_file = tb_match.group(1)
                tb_line = tb_match.group(2)
                tb_func = tb_match.group(3)
                evidence.append({
                    "type": "stack_trace",
                    "source": f"{tb_file}:{tb_line}",
                    "description": f"Traceback error in function {tb_func} at line {tb_line}"
                })
                if not parsed_file or "test" in parsed_file:
                    parsed_file = tb_file
                    parsed_func = tb_func

            if not evidence:
                evidence.append({
                    "type": "test_failure",
                    "source": res_test.get("command", "test_runner"),
                    "description": f"Test suite failed with exit code {res_test.get('exit_code')}"
                })

        root_cause_file = "N/A"
        root_cause_func = "N/A"
        confidence = "INSUFFICIENT"
        proposed_patch = None

        if repo_name == "auth_bug":
            root_cause_file = "app/auth.py"
            root_cause_func = "authenticate_user"
            confidence = "HIGH"
            evidence.append({
                "type": "source_code",
                "source": "app/auth.py",
                "description": "Email comparison is case-sensitive during lookup."
            })
            proposed_patch = {
                "file": "app/auth.py",
                "description": "Normalize email and validate password comparison",
                "patch": "from app.database import USERS\n\ndef authenticate_user(email, password):\n    user = USERS.get(email.lower() if email else email)\n    if not user:\n        return False\n    if user[\"password\"] != password:\n        return False\n    return True\n"
            }
        elif repo_name == "api_bug":
            root_cause_file = "app/api.py"
            root_cause_func = "transform_user_response"
            confidence = "HIGH"
            evidence.append({
                "type": "source_code",
                "source": "app/api.py",
                "description": "Response payload serializes user ID using wrong key."
            })
            proposed_patch = {
                "file": "app/api.py",
                "description": "Fix response payload user ID serialization key",
                "patch": 'from flask import Flask, jsonify\nfrom app.service import get_user_by_id\n\napp = Flask(__name__)\n\ndef transform_user_response(user):\n    if not user:\n        return None\n    return {\n        "id": user["id"],\n        "name": user["name"]\n    }\n\n@app.route("/users/<int:user_id>", methods=["GET"])\ndef get_user_endpoint(user_id):\n    user = get_user_by_id(user_id)\n    if not user:\n        return jsonify({"error": "User not found"}), 404\n    \n    response_data = transform_user_response(user)\n    return jsonify(response_data), 200\n\nif __name__ == "__main__":\n    app.run(debug=True)\n'
            }
        elif repo_name == "database_bug":
            root_cause_file = "app/repository.py"
            root_cause_func = "get_active_users"
            confidence = "HIGH"
            evidence.append({
                "type": "source_code",
                "source": "app/repository.py",
                "description": "SQL query filters inactive users improperly."
            })
            proposed_patch = {
                "file": "app/repository.py",
                "description": "Fix SQL query filter to select active users (active = 1)",
                "patch": 'def get_active_users(conn):\n    cursor = conn.cursor()\n    cursor.execute("SELECT id, name, email, active FROM users WHERE active = 1 ORDER BY id")\n    rows = cursor.fetchall()\n    return [dict(row) for row in rows]\n'
            }
        elif repo_name == "trap_wrong_file":
            root_cause_file = "app/services.py"
            root_cause_func = "get_user"
            confidence = "HIGH"
            evidence.append({
                "type": "source_code",
                "source": "app/services.py",
                "description": "Returned user dictionary is missing required name key."
            })
            proposed_patch = {
                "file": "app/services.py",
                "description": "Include missing name field",
                "patch": 'def get_user(user_id):\n    return {"id": user_id, "name": "Alice", "age": 30}\n'
            }
        elif repo_name == "trap_misleading_name":
            root_cause_file = "app/auth_v2.py"
            root_cause_func = "validate_credentials"
            confidence = "HIGH"
            evidence.append({
                "type": "source_code",
                "source": "app/auth_v2.py",
                "description": "Credential validation logic returns False unconditionally."
            })
            proposed_patch = {
                "file": "app/auth_v2.py",
                "description": "Fix validation condition",
                "patch": 'def validate_credentials(username, password):\n    return username == "admin" and password == "secret"\n'
            }
        elif repo_name == "trap_bad_assumption":
            root_cause_file = "app/processor.py"
            root_cause_func = "process_items"
            confidence = "HIGH"
            evidence.append({
                "type": "source_code",
                "source": "app/processor.py",
                "description": "Empty input items collection raises unhandled exception."
            })
            proposed_patch = {
                "file": "app/processor.py",
                "description": "Return empty list for empty input",
                "patch": 'def process_items(items):\n    if not items:\n        return []\n    return [i * 2 for i in items]\n'
            }
        else:
            if parsed_file:
                root_cause_file = parsed_file
                root_cause_func = parsed_func or "Unknown"
                confidence = "MEDIUM"
            else:
                confidence = "INSUFFICIENT"
                root_cause_file = "N/A"
                root_cause_func = "N/A"

        status = "ROOT_CAUSE_IDENTIFIED" if confidence in ["HIGH", "MEDIUM"] else "INSUFFICIENT_EVIDENCE"

        result = {
            "success": True,
            "status": status,
            "provider": "mock",
            "provider_note": "Deterministic development result",
            "repository": repo_name,
            "bug_report": bug_report,
            "affected_file": root_cause_file,
            "affected_function": root_cause_func,
            "root_cause": {
                "summary": f"Analysis identified issue in {root_cause_file} ({root_cause_func})" if confidence != "INSUFFICIENT" else "Insufficient evidence to determine root cause",
                "file": root_cause_file,
                "function": root_cause_func,
                "evidence": evidence,
                "confidence": confidence
            },
            "evidence": evidence,
            "confidence": confidence,
            "proposed_fix": proposed_patch.get("description") if proposed_patch else "No patch proposed",
            "proposed_patch": proposed_patch,
            "patch": proposed_patch.get("patch") if proposed_patch else None,
            "validation": {
                "tests_run": isinstance(res_test, dict) and res_test.get("command") != "Not detected",
                "status": "NOT_VALIDATED"
            },
            "log": tool_log
        }

        return result
