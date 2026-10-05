import json

import os

import re
from pathlib import Path

from dotenv import load_dotenv

# Load the backend/.env explicitly so this provider works even when the
# Flask process was started from a different working directory.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
_ENV_FILE = _BACKEND_DIR / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)

from ...config import Config

from typing import Any, Callable, Dict, List, Optional



import google.generativeai as genai



from .base import LLMProvider
# ============================================================# SYSTEM PROMPT# ============================================================
SYSTEM_PROMPT = """

You are DEVGUARD AI, an evidence-first autonomous software debugging engineer.



Your job is to investigate real software repositories using actual evidence.



IMPORTANT RULES:



1. Never invent:

   - files

   - functions

   - source code

   - test results

   - tracebacks

   - errors

   - Git history

   - patches



2. Deterministic repository and test-tool output is authoritative.



3. Inspect source code and tests before identifying a root cause.

4. Distinguish symptoms from root causes.



5. Every root-cause claim must be supported by concrete evidence.



6. Use repository tools when more evidence is required.



7. Do not modify the repository yourself.



8. The proposed patch must be based on actual source code.



9. If evidence is insufficient, explicitly return INSUFFICIENT_EVIDENCE.



10. Never claim that tests pass unless an actual test execution proves it.

11. Prefer high-value executable evidence over documentation. Do not read
    README.md, WORKSHOP.md, or other general documentation unless necessary
    to resolve ambiguity after relevant tests, source, traceback, imports, and
    functions have been exhausted.

12. Use the minimum number of tool calls required to establish an
    evidence-backed root cause. Avoid duplicate file reads and exploratory
    documentation reads. The read tool enforces an evidence budget.



Return exactly ONE JSON object.



Required schema:



{

    "status": "ROOT_CAUSE_IDENTIFIED" | "INSUFFICIENT_EVIDENCE",



    "affected_file": "relative/path.py",



    "affected_function": "function_name",



    "root_cause": {

        "summary": "Clear evidence-backed root cause.",

        "file": "relative/path.py",

        "function": "function_name",

        "evidence": [

            {

                "type": "test_failure",

                "source": "tests/test_example.py:10",

                "description": "Concrete evidence."

            }

        ],

        "confidence": "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT"

    },



    "evidence": [],



    "confidence": "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT",



    "proposed_fix": "Minimal fix description.",



    "proposed_patch": {

        "file": "relative/path.py",

        "description": "What should change.",

        "patch": "FULL replacement content of target file"

    }

}



If evidence is insufficient:



{

    "status": "INSUFFICIENT_EVIDENCE",

    "affected_file": "N/A",

    "affected_function": "N/A",

    "root_cause": {

        "summary": "Insufficient evidence.",

        "file": "N/A",

        "function": "N/A",

        "evidence": [],

        "confidence": "INSUFFICIENT"

    },

    "evidence": [],

    "confidence": "INSUFFICIENT",

    "proposed_fix": "No patch proposed.",

    "proposed_patch": null

}



Return ONLY JSON when producing the final investigation result.

"""
# ============================================================# GEMINI PROVIDER# ============================================================
class GeminiProvider(LLMProvider):
# ========================================================# MAIN INVESTIGATION# ========================================================
    def investigate(

        self,

        repo_path: str,

        repo_name: str,

        bug_report: Any,

        tools: List[Callable],

    ) -> Dict[str, Any]:



        print(

            f"[GEMINI][MODULE] Loaded from: {__file__}",

            flush=True,

        )



        print(

            "[GEMINI][INVESTIGATE] GeminiProvider.investigate() entered",

            flush=True,

        )
# ----------------------------------------------------# API KEY# ----------------------------------------------------
        api_key = os.getenv("GEMINI_API_KEY") or getattr(Config, "GEMINI_API_KEY", "")



        if not api_key:



            print(

                "[GEMINI][ERROR] GEMINI_API_KEY is missing",

                flush=True,

            )



            return self._error_result(

                "missing_api_key",

                "GEMINI_API_KEY is not configured",

                repo_name,

                bug_report,

            )
# ----------------------------------------------------# CONFIGURE GEMINI# ----------------------------------------------------
        try:

            genai.configure(api_key=api_key)



            print(

                "[GEMINI][CONFIG] Gemini API configured",

                flush=True,

            )



        except Exception as exc:



            print(

                f"[GEMINI][CONFIG_ERROR] {exc}",

                flush=True,

            )



            return self._handle_error(

                exc,

                [],

                repo_name,

                bug_report,

            )
# ----------------------------------------------------# MODEL# ----------------------------------------------------
        model_name = os.getenv("GEMINI_MODEL") or getattr(Config, "GEMINI_MODEL", "gemini-1.5-flash")



        try:



            max_calls = max(

                1,

                int(

                    os.environ.get(

                        "MAX_TOOL_CALLS",

                        "12",

                    )

                ),

            )



        except ValueError:



            max_calls = 12



        print(

            f"[GEMINI][CONFIG] Model={model_name}",

            flush=True,

        )



        print(

            f"[GEMINI][CONFIG] MAX_TOOL_CALLS={max_calls}",

            flush=True,

        )
# ----------------------------------------------------# BUILD INITIAL PROMPT# ----------------------------------------------------
        if isinstance(bug_report, dict):



            prompt = self._build_evidence_prompt(

                repo_name,

                bug_report,

            )



        else:



            prompt = (

                f"Repository: {repo_name}\n\n"

                f"Bug Report / Direction:\n"

                f"{bug_report or 'Autonomous Discovery'}\n\n"

                "Investigate the repository using the supplied "

                "tools and return the required JSON."

            )
# IMPORTANT:# These logs are now outside the if/else block.# This fixes misleading/missing REQUEST_STARTED logs.
        print(

            "[GEMINI] REQUEST_STARTED",

            flush=True,

        )



        print(

            f"[DEVGUARD] Gemini request started for "

            f"{repo_name} using {model_name}",

            flush=True,

        )



        print(

            f"[GEMINI][PROMPT] Prompt length={len(prompt)}",

            flush=True,

        )
# ----------------------------------------------------# TOOL LOG# ----------------------------------------------------
        tool_log: List[str] = []
# ----------------------------------------------------# CREATE MODEL# ----------------------------------------------------
        try:



            print(

                "[GEMINI][MODEL] Creating GenerativeModel...",

                flush=True,

            )



            model = genai.GenerativeModel(

                model_name=model_name,

                system_instruction=SYSTEM_PROMPT,

                tools=tools,

            )



            print(

                "[GEMINI][MODEL] GenerativeModel created",

                flush=True,

            )



            chat = model.start_chat(

                enable_automatic_function_calling=False

            )



            print(

                "[GEMINI][CHAT] Chat session created",

                flush=True,

            )



        except Exception as exc:



            print(

                f"[GEMINI][MODEL_ERROR] "

                f"{type(exc).__name__}: {exc}",

                flush=True,

            )



            return self._handle_error(

                exc,

                tool_log,

                repo_name,

                bug_report,

            )
# ----------------------------------------------------# FIRST GEMINI REQUEST# ----------------------------------------------------
        try:



            print(

                "[GEMINI][SEND] Calling chat.send_message()",

                flush=True,

            )



            response = chat.send_message(prompt)



            print(

                "[GEMINI] REQUEST_COMPLETED",

                flush=True,

            )



            response_text = self._safe_response_text(

                response

            )



            print(

                "[GEMINI] RAW_RESPONSE_RECEIVED",

                flush=True,

            )



            print(

                f"[GEMINI] RESPONSE_TYPE="

                f"{type(response).__name__}",

                flush=True,

            )



            print(

                f"[GEMINI] RESPONSE_TEXT_LENGTH="

                f"{len(response_text)}",

                flush=True,

            )



        except Exception as exc:



            print(

                f"[DEVGUARD][GEMINI_ERROR] "

                f"{type(exc).__name__}: {exc}",

                flush=True,

            )



            return self._handle_error(

                exc,

                tool_log,

                repo_name,

                bug_report,

            )
# ----------------------------------------------------# TOOL MAP# ----------------------------------------------------
        tool_map: Dict[str, Callable] = {}



        for tool in tools:



            name = getattr(

                tool,

                "__name__",

                None,

            )



            if name:

                tool_map[name] = tool



        print(

            f"[GEMINI][TOOLS] Registered tools="

            f"{list(tool_map.keys())}",

            flush=True,

        )
# ====================================================# AGENT LOOP# ====================================================
        for iteration in range(max_calls):



            print(

                f"[DEVGUARD][AGENT_LOOP] "

                f"iteration={iteration + 1}/{max_calls}",

                flush=True,

            )
# ------------------------------------------------# CHECK FOR FUNCTION CALLS# ------------------------------------------------
            function_calls = self._extract_function_calls(

                response

            )



            print(

                f"[DEVGUARD][AGENT_LOOP] "

                f"function_calls={len(function_calls)}",

                flush=True,

            )
# ------------------------------------------------# NO TOOL CALL# ------------------------------------------------
            if not function_calls:



                response_text = (

                    getattr(

                        response,

                        "text",

                        "",

                    )

                    or ""

                ).strip()



                print(

                    "[DEVGUARD][GEMINI_RESPONSE_TEXT]",

                    flush=True,

                )



                print(

                    response_text,

                    flush=True,

                )
# --------------------------------------------# PARSE JSON# --------------------------------------------
                print(

                    "[GEMINI] PARSE_STARTED",

                    flush=True,

                )



                parsed = self._parse_json_response(

                    response_text

                )



                if parsed is not None:



                    print(

                        "[GEMINI] PARSE_SUCCESS",

                        flush=True,

                    )



                    print(

                        "[GEMINI][PARSED_RESULT]",

                        flush=True,

                    )



                    print(

                        json.dumps(

                            parsed,

                            indent=2,

                            default=str,

                        ),

                        flush=True,

                    )
# ----------------------------------------# PATCH GENERATION# ----------------------------------------
                    parsed = self._ensure_patch(

                        parsed=parsed,

                        chat=chat,

                        tool_map=tool_map,

                        repo_name=repo_name,

                        bug_report=bug_report,

                        tool_log=tool_log,

                    )



                    return self._finalize_result(

                        parsed,

                        repo_name,

                        bug_report,

                        tool_log,

                    )
# --------------------------------------------# JSON PARSE FAILED# --------------------------------------------
                print(

                    "[GEMINI] PARSE_FAILURE",

                    flush=True,

                )
# Ask Gemini to return valid JSON.
                try:



                    print(

                        "[GEMINI][RETRY] Requesting valid JSON",

                        flush=True,

                    )



                    response = chat.send_message(

                        """

Return ONLY one valid JSON object using the exact

schema from the system instructions.



Do not use markdown.



Do not include explanations.



Do not include ```json fences.

"""

                    )



                    retry_text = (

                        getattr(

                            response,

                            "text",

                            "",

                        )

                        or ""

                    ).strip()



                    print(

                        "[GEMINI][RETRY] Response received",

                        flush=True,

                    )



                    print(

                        f"[GEMINI][RETRY] "

                        f"Response length={len(retry_text)}",

                        flush=True,

                    )



                    parsed = self._parse_json_response(

                        retry_text

                    )



                    if parsed is not None:



                        print(

                            "[GEMINI][RETRY] PARSE_SUCCESS",

                            flush=True,

                        )



                        parsed = self._ensure_patch(

                            parsed=parsed,

                            chat=chat,

                            tool_map=tool_map,

                            repo_name=repo_name,

                            bug_report=bug_report,

                            tool_log=tool_log,

                        )



                        return self._finalize_result(

                            parsed,

                            repo_name,

                            bug_report,

                            tool_log,

                        )



                    print(

                        "[GEMINI][RETRY] PARSE_FAILURE",

                        flush=True,

                    )



                except Exception as exc:



                    print(

                        f"[GEMINI][RETRY_ERROR] "

                        f"{type(exc).__name__}: {exc}",

                        flush=True,

                    )



                    return self._handle_error(

                        exc,

                        tool_log,

                        repo_name,

                        bug_report,

                    )



                continue
# =================================================# TOOL CALLS# =================================================
            print(

                f"[DEVGUARD][TOOL_CALLS] "

                f"{len(function_calls)} tool call(s)",

                flush=True,

            )



            function_responses = []



            for function_call in function_calls:



                func_name = getattr(

                    function_call,

                    "name",

                    None,

                )



                if not func_name:

                    continue
# --------------------------------------------# TOOL ARGUMENTS# --------------------------------------------
                try:



                    args = dict(

                        getattr(

                            function_call,

                            "args",

                            {},

                        )

                    )



                except Exception:



                    args = {}



                print(

                    f"[DEVGUARD][TOOL] "

                    f"{func_name} args={args}",

                    flush=True,

                )



                tool_log.append(

                    f"Gemini requested {func_name} "

                    f"with {args}"

                )
# --------------------------------------------# EXECUTE TOOL# --------------------------------------------
                if func_name not in tool_map:



                    result = {

                        "success": False,

                        "error": (

                            f"Unknown tool: {func_name}"

                        ),

                    }



                else:



                    try:



                        result = tool_map[

                            func_name

                        ](**args)



                    except Exception as exc:



                        print(

                            f"[DEVGUARD][TOOL_ERROR] "

                            f"{func_name}: {exc}",

                            flush=True,

                        )



                        result = {

                            "success": False,

                            "error": str(exc),

                        }
# --------------------------------------------# TOOL RESULT# --------------------------------------------
                result_str = str(result)



                print(

                    f"[DEVGUARD][TOOL_RESULT] "

                    f"{func_name}: "

                    f"{result_str[:2000]}",

                    flush=True,

                )



                tool_log.append(

                    f"Tool result: "

                    f"{result_str[:1200]}"

                )
# --------------------------------------------# GEMINI FUNCTION RESPONSE# --------------------------------------------
                try:



                    function_response = (

                        genai.protos.Part(

                            function_response=(

                                genai.protos.FunctionResponse(

                                    name=func_name,

                                    response=(

                                        self._safe_tool_response(

                                            result

                                        )

                                    ),

                                )

                            )

                        )

                    )



                    function_responses.append(

                        function_response

                    )



                except Exception as exc:



                    print(

                        f"[DEVGUARD][FUNCTION_RESPONSE_ERROR] "

                        f"{exc}",

                        flush=True,

                    )
# ------------------------------------------------# NO FUNCTION RESPONSES# ------------------------------------------------
            if not function_responses:



                print(

                    "[DEVGUARD][TOOL] "

                    "No valid function responses generated",

                    flush=True,

                )



                continue
# ------------------------------------------------# SEND TOOL RESULTS TO GEMINI# ------------------------------------------------
            try:



                print(

                    "[DEVGUARD][GEMINI] "

                    "Sending tool results back...",

                    flush=True,

                )



                response = chat.send_message(

                    function_responses

                )



                print(

                    "[DEVGUARD][GEMINI_AFTER_TOOL]",

                    flush=True,

                )



                print(

                    self._safe_response_text(

                        response

                    ),

                    flush=True,

                )



            except Exception as exc:



                print(

                    f"[DEVGUARD][GEMINI_TOOL_ERROR] "

                    f"{type(exc).__name__}: {exc}",

                    flush=True,

                )



                return self._handle_error(

                    exc,

                    tool_log,

                    repo_name,

                    bug_report,

                )
# ====================================================# MAX ITERATIONS REACHED# ====================================================
        print(

            "[GEMINI] FINAL_RESULT "

            "status=LLM_RESPONSE_PARSE_ERROR",

            flush=True,

        )



        return {

            "success": False,

            "status": "LLM_RESPONSE_PARSE_ERROR",

            "provider": "gemini",

            "error_type": "malformed_response",

            "message": (

                "Gemini did not return a valid "

                "JSON investigation result."

            ),

            "repository": repo_name,

            "bug_report": bug_report,

            "affected_file": "N/A",

            "affected_function": "N/A",

            "root_cause": {

                "summary": (

                    "Gemini response could not "

                    "be parsed."

                ),

                "file": "N/A",

                "function": "N/A",

                "evidence": [],

                "confidence": "INSUFFICIENT",

            },

            "evidence": [],

            "confidence": "INSUFFICIENT",

            "proposed_fix": "No patch proposed.",

            "proposed_patch": None,

            "log": tool_log,

        }
# ========================================================# EXTRACT FUNCTION CALLS# ========================================================
    @staticmethod

    def _extract_function_calls(

        response: Any,

    ) -> List[Any]:



        calls = []



        try:



            for part in getattr(

                response,

                "parts",

                [],

            ):



                function_call = getattr(

                    part,

                    "function_call",

                    None,

                )



                if function_call:

                    calls.append(function_call)



        except Exception as exc:



            print(

                f"[GEMINI][FUNCTION_CALL_PARSE_ERROR] "

                f"{exc}",

                flush=True,

            )



            return []



        return calls
# ========================================================# BUILD EVIDENCE PROMPT# ========================================================
    @staticmethod

    def _build_evidence_prompt(

        repo_name: str,

        context: Dict[str, Any],

    ) -> str:



        repository_metadata = json.dumps(

            context.get(

                "repository_metadata",

                {},

            ),

            indent=2,

            default=str,

        )



        test_result = json.dumps(

            context.get(

                "test_result",

                {},

            ),

            indent=2,

            default=str,

        )



        deterministic_evidence = json.dumps(

            context.get(

                "deterministic_evidence",

                [],

            ),

            indent=2,

            default=str,

        )



        source_code = json.dumps(

            context.get(

                "source_code_inspected",

                {},

            ),

            indent=2,

            default=str,

        )



        search_results = json.dumps(

            context.get(

                "repository_search_results",

                [],

            ),

            indent=2,

            default=str,

        )



        existing_files = json.dumps(

            context.get(

                "existing_files_in_repo",

                [],

            ),

            indent=2,

            default=str,

        )



        git_history = json.dumps(

            context.get(

                "git_history",

                [],

            ),

            indent=2,

            default=str,

        )



        git_diff = json.dumps(

            context.get(

                "git_diff",

                {},

            ),

            indent=2,

            default=str,

        )



        return (

            f"Repository: {repo_name}\n\n"



            f"Investigation mode:\n"

            f"{context.get('investigation_mode', 'autonomous')}\n\n"



            f"Bug report / direction:\n"

            f"{context.get('bug_report') or 'Autonomous Discovery'}\n\n"



            "==================================================\n"

            "REPOSITORY METADATA\n"

            "==================================================\n"

            f"{repository_metadata}\n\n"



            "==================================================\n"

            "DETERMINISTIC TEST EXECUTION\n"

            "==================================================\n"

            f"{test_result}\n\n"



            "==================================================\n"

            "DETERMINISTIC EVIDENCE\n"

            "==================================================\n"

            f"{deterministic_evidence}\n\n"



            "==================================================\n"

            "INSPECTED SOURCE / TEST FILES\n"

            "==================================================\n"

            f"{source_code}\n\n"



            "==================================================\n"

            "REPOSITORY SEARCH RESULTS\n"

            "==================================================\n"

            f"{search_results}\n\n"



            "==================================================\n"

            "EXISTING FILES\n"

            "==================================================\n"

            f"{existing_files}\n\n"



            "==================================================\n"

            "GIT HISTORY\n"

            "==================================================\n"

            f"{git_history}\n\n"



            "==================================================\n"

            "GIT DIFF\n"

            "==================================================\n"

            f"{git_diff}\n\n"



            "==================================================\n"

            "INVESTIGATION INSTRUCTIONS\n"

            "==================================================\n"



            "Use the supplied evidence and repository tools.\n\n"



            "Do not blindly trust the bug report.\n\n"



            "Trace the actual failure to its root cause.\n\n"



            "Separate symptoms from causes.\n\n"



            "If the supplied evidence is insufficient, "

            "use the repository tools to gather more evidence.\n\n"



            "Inspect the actual affected source file before "
            "proposing a patch.\n\n"

            "Prefer high-value executable evidence over documentation. "
            "Do not read README.md, WORKSHOP.md, or other general "
            "documentation unless necessary to resolve ambiguity after "
            "relevant tests, source, traceback, imports, and functions have "
            "been exhausted. Avoid duplicate reads and use the minimum "
            "number of tool calls required.\n\n"

            "Return ONLY the required JSON."

        )
# ========================================================# PARSE JSON# ========================================================
    @staticmethod

    def _parse_json_response(

        text: str,

    ) -> Optional[Dict[str, Any]]:



        if not text:

            return None



        cleaned = text.strip()
# ----------------------------------------------------# Remove markdown fences# ----------------------------------------------------
        if cleaned.startswith("```"):



            cleaned = re.sub(

                r"^```(?:json)?\s*",

                "",

                cleaned,

                flags=re.IGNORECASE,

            )



            cleaned = re.sub(

                r"\s*```$",

                "",

                cleaned,

            ).strip()
# ----------------------------------------------------# Direct JSON# ----------------------------------------------------
        try:



            parsed = json.loads(cleaned)



            if isinstance(parsed, dict):

                return parsed



        except json.JSONDecodeError:

            pass
# ----------------------------------------------------# Find JSON object inside response# ----------------------------------------------------
        start = cleaned.find("{")



        if start == -1:

            return None



        depth = 0

        in_string = False

        escaped = False



        for index in range(

            start,

            len(cleaned),

        ):



            char = cleaned[index]



            if escaped:



                escaped = False

                continue



            if char == "\\\\" and in_string:



                escaped = True

                continue



            if char == '"':



                in_string = not in_string

                continue



            if in_string:

                continue



            if char == "{":



                depth += 1



            elif char == "}":



                depth -= 1



                if depth == 0:



                    candidate = cleaned[

                        start:index + 1

                    ]



                    try:



                        parsed = json.loads(

                            candidate

                        )



                        if isinstance(

                            parsed,

                            dict,

                        ):

                            return parsed



                    except json.JSONDecodeError:



                        return None



        return None
# ========================================================# ENSURE PATCH# ========================================================
    def _ensure_patch(

        self,

        parsed: Dict[str, Any],

        chat: Any,

        tool_map: Dict[str, Callable],

        repo_name: str,

        bug_report: Any,

        tool_log: List[str],

    ) -> Dict[str, Any]:



        if not isinstance(parsed, dict):

            return parsed



        status = str(

            parsed.get(

                "status",

                "",

            )

        ).upper()
# ----------------------------------------------------# No root cause -> no patch# ----------------------------------------------------
        if status != "ROOT_CAUSE_IDENTIFIED":



            return parsed
# ----------------------------------------------------# Already has valid patch# ----------------------------------------------------
        if self._valid_proposed_patch(

            parsed.get("proposed_patch")

        ):



            print(

                "[DEVGUARD][PATCH] "

                "Valid proposed_patch already supplied.",

                flush=True,

            )



            return parsed



        print(

            "[DEVGUARD][PATCH] "

            "Root cause identified without a valid patch.",

            flush=True,

        )



        print(

            "[DEVGUARD][PATCH] "

            "Starting dedicated patch-generation phase.",

            flush=True,

        )



        patch_prompt = """

The investigation identified a root cause but the previous JSON

does not contain a usable proposed_patch.



Now perform the PATCH GENERATION phase.



Requirements:



1. Use the affected_file from the root-cause result.



2. If the affected source file has not been inspected,

   call read_repository_file for it.



3. Use the actual source code and test evidence.



4. Produce the smallest safe fix.



5. Do not modify the repository.



6. Return ONLY one JSON object.



Required structure:



{

    "status": "ROOT_CAUSE_IDENTIFIED",

    "affected_file": "relative/path.py",

    "affected_function": "function_name",



    "root_cause": {

        "summary": "same evidence-backed root cause",

        "file": "relative/path.py",

        "function": "function_name",

        "evidence": [],

        "confidence": "HIGH"

    },



    "evidence": [],



    "confidence": "HIGH",



    "proposed_fix": "minimal fix description",



    "proposed_patch": {

        "file": "relative/path.py",

        "description": "what the patch changes",

        "patch": "FULL replacement content of target file"

    }

}



IMPORTANT:



- proposed_patch MUST NOT be null.

- patch MUST contain actual source code.

- Do not use markdown fences.

- Do not return a unified diff.

- Do not invent source code.

"""



        try:



            print(

                "[DEVGUARD][PATCH] "

                "Sending patch-generation request...",

                flush=True,

            )



            response = chat.send_message(

                patch_prompt

            )



            print(

                "[DEVGUARD][PATCH] "

                "Patch request completed.",

                flush=True,

            )



            for patch_iteration in range(4):



                print(

                    f"[DEVGUARD][PATCH_LOOP] "

                    f"iteration={patch_iteration + 1}/4",

                    flush=True,

                )
# --------------------------------------------# PATCH TOOL CALLS# --------------------------------------------
                function_calls = (

                    self._extract_function_calls(

                        response

                    )

                )



                if function_calls:



                    function_responses = []



                    for function_call in function_calls:



                        func_name = getattr(

                            function_call,

                            "name",

                            None,

                        )



                        if not func_name:

                            continue



                        try:



                            args = dict(

                                getattr(

                                    function_call,

                                    "args",

                                    {},

                                )

                            )



                        except Exception:



                            args = {}



                        print(

                            f"[DEVGUARD][PATCH_TOOL] "

                            f"{func_name} args={args}",

                            flush=True,

                        )



                        tool_log.append(

                            f"Patch phase requested "

                            f"{func_name} with {args}"

                        )



                        if func_name not in tool_map:



                            result = {

                                "success": False,

                                "error": (

                                    f"Unknown tool: "

                                    f"{func_name}"

                                ),

                            }



                        else:



                            try:



                                result = tool_map[

                                    func_name

                                ](**args)



                            except Exception as exc:



                                result = {

                                    "success": False,

                                    "error": str(exc),

                                }



                        print(

                            f"[DEVGUARD][PATCH_TOOL_RESULT] "

                            f"{func_name}: "

                            f"{str(result)[:2000]}",

                            flush=True,

                        )



                        try:



                            function_responses.append(

                                genai.protos.Part(

                                    function_response=(

                                        genai.protos.FunctionResponse(

                                            name=func_name,

                                            response=(

                                                self._safe_tool_response(

                                                    result

                                                )

                                            ),

                                        )

                                    )

                                )

                            )



                        except Exception as exc:



                            print(

                                f"[DEVGUARD][PATCH_FUNCTION_RESPONSE_ERROR] "

                                f"{exc}",

                                flush=True,

                            )



                    if function_responses:



                        print(

                            "[DEVGUARD][PATCH] "

                            "Sending tool results...",

                            flush=True,

                        )



                        response = (

                            chat.send_message(

                                function_responses

                            )

                        )



                        continue
# --------------------------------------------# PARSE PATCH RESPONSE# --------------------------------------------
                response_text = (

                    getattr(

                        response,

                        "text",

                        "",

                    )

                    or ""

                ).strip()



                candidate = (

                    self._parse_json_response(

                        response_text

                    )

                )



                if candidate is not None:



                    if self._valid_proposed_patch(

                        candidate.get(

                            "proposed_patch"

                        )

                    ):



                        print(

                            "[DEVGUARD][PATCH] "

                            "Valid proposed_patch received.",

                            flush=True,

                        )



                        return candidate
# ----------------------------------------# Normalize top-level patch if necessary# ----------------------------------------
                    normalized_patch = candidate.get(

                        "patch"

                    )



                    if (

                        isinstance(

                            normalized_patch,

                            str,

                        )

                        and normalized_patch.strip()

                    ):



                        candidate[

                            "proposed_patch"

                        ] = {



                            "file": candidate.get(

                                "affected_file",

                                "N/A",

                            ),



                            "description": candidate.get(

                                "proposed_fix",

                                "Generated source patch.",

                            ),



                            "patch": normalized_patch,

                        }



                        if self._valid_proposed_patch(

                            candidate[

                                "proposed_patch"

                            ]

                        ):



                            print(

                                "[DEVGUARD][PATCH] "

                                "Normalized top-level patch.",

                                flush=True,

                            )



                            return candidate
# --------------------------------------------# Ask again# --------------------------------------------
                print(

                    "[DEVGUARD][PATCH] "

                    "Patch response incomplete. "

                    "Requesting complete source.",

                    flush=True,

                )



                response = chat.send_message(

                    """

Return ONLY the JSON object.



The previous response is incomplete because

proposed_patch.patch is missing or invalid.



You MUST provide:



proposed_patch.file

proposed_patch.description

proposed_patch.patch



The patch field must contain the COMPLETE

replacement source code of the affected file.



Do not use markdown fences.



Do not use diff markers.



Do not return ROOT_CAUSE_IDENTIFIED

without proposed_patch.

"""

                )



            print(

                "[DEVGUARD][PATCH] "

                "Patch generation exhausted.",

                flush=True,

            )



        except Exception as exc:



            print(

                f"[DEVGUARD][PATCH_ERROR] "

                f"{type(exc).__name__}: {exc}",

                flush=True,

            )



            tool_log.append(

                f"Patch generation failed: {exc}"

            )



        parsed["proposed_patch"] = None



        return parsed
# ========================================================# VALIDATE PROPOSED PATCH# ========================================================
    @staticmethod

    def _valid_proposed_patch(

        patch: Any,

    ) -> bool:



        if not isinstance(

            patch,

            dict,

        ):

            return False



        file_name = patch.get("file")

        description = patch.get("description")

        content = patch.get("patch")



        if not isinstance(

            file_name,

            str,

        ):

            return False



        if not file_name.strip():

            return False



        if file_name.strip().lower() in {

            "n/a",

            "none",

            "null",

        }:

            return False



        if not isinstance(

            description,

            str,

        ):

            return False



        if not description.strip():

            return False



        if not isinstance(

            content,

            str,

        ):

            return False



        if not content.strip():

            return False



        lowered = content.strip().lower()



        if lowered in {

            "patch",

            "full replacement content of the target file",

            "...",

            "todo",

        }:

            return False



        return True
# ========================================================# FINALIZE RESULT# ========================================================
    def _finalize_result(

        self,

        parsed: Dict[str, Any],

        repo_name: str,

        bug_report: Any,

        tool_log: List[str],

    ) -> Dict[str, Any]:



        status = str(

            parsed.get(

                "status",

                "INSUFFICIENT_EVIDENCE",

            )

        ).upper()



        confidence = str(

            parsed.get(

                "confidence",

                "INSUFFICIENT",

            )

        ).upper()



        affected_file = (

            parsed.get(

                "affected_file"

            )

            or "N/A"

        )



        affected_function = (

            parsed.get(

                "affected_function"

            )

            or "N/A"

        )



        root_cause = parsed.get(

            "root_cause",

            {},

        )



        if not isinstance(

            root_cause,

            dict,

        ):

            root_cause = {}



        root_evidence = root_cause.get(

            "evidence",

            [],

        )



        evidence = parsed.get(

            "evidence",

            [],

        )



        if not isinstance(

            root_evidence,

            list,

        ):

            root_evidence = [

                str(root_evidence)

            ]



        if not isinstance(

            evidence,

            list,

        ):

            evidence = [

                str(evidence)

            ]
# ----------------------------------------------------# IMPORTANT:# Do NOT automatically mark root cause insufficient# just because Gemini's separate evidence array is empty.## Root-cause evidence can be inside root_cause.evidence.# ----------------------------------------------------
        all_evidence = (

            root_evidence

            + evidence

        )



        if (

            status == "ROOT_CAUSE_IDENTIFIED"

            and not all_evidence

        ):



            print(

                "[DEVGUARD][FINALIZE] "

                "Root cause has no evidence.",

                flush=True,

            )



            return self._insufficient_result(

                repo_name,

                bug_report,

                tool_log,

                (

                    "Gemini identified a possible root cause "

                    "without sufficient supporting evidence."

                ),

            )
# ----------------------------------------------------# Confidence validation# ----------------------------------------------------
        if confidence == "INSUFFICIENT":



            return self._insufficient_result(

                repo_name,

                bug_report,

                tool_log,

                root_cause.get(

                    "summary",

                    (

                        "Insufficient evidence "

                        "to determine root cause."

                    ),

                ),

            )



        proposed_patch = parsed.get(

            "proposed_patch"

        )
# ----------------------------------------------------# Never manufacture patches# ----------------------------------------------------
        if status == "ROOT_CAUSE_IDENTIFIED":



            if not self._valid_proposed_patch(

                proposed_patch

            ):



                parsed[

                    "proposed_patch"

                ] = None



                parsed[

                    "patch"

                ] = None



        result = {

            "success": True,



            "status": status,



            "provider": "gemini",



            "repository": repo_name,



            "bug_report": bug_report,



            "affected_file": affected_file,



            "affected_function": affected_function,



            "root_cause": {

                "summary": root_cause.get(

                    "summary",

                    "No root cause identified.",

                ),



                "file": root_cause.get(

                    "file",

                    affected_file,

                ),



                "function": root_cause.get(

                    "function",

                    affected_function,

                ),



                "evidence": root_evidence,



                "confidence": confidence,

            },



            "evidence": evidence,



            "confidence": confidence,



            "proposed_fix": parsed.get(

                "proposed_fix",

                "No patch proposed.",

            ),



            "proposed_patch": (

                parsed.get(

                    "proposed_patch"

                )

                if self._valid_proposed_patch(

                    parsed.get(

                        "proposed_patch"

                    )

                )

                else None

            ),



            "log": tool_log,

        }



        print(

            "[DEVGUARD][FINAL_RESULT] "

            f"status={status} "

            f"confidence={confidence} "

            f"file={affected_file} "

            f"function={affected_function}",

            flush=True,

        )



        return result
# ========================================================# INSUFFICIENT RESULT# ========================================================
    @staticmethod

    def _insufficient_result(

        repo_name: str,

        bug_report: Any,

        tool_log: List[str],

        summary: str,

    ) -> Dict[str, Any]:



        return {

            "success": True,



            "status": "INSUFFICIENT_EVIDENCE",



            "provider": "gemini",



            "repository": repo_name,



            "bug_report": bug_report,



            "affected_file": "N/A",



            "affected_function": "N/A",



            "root_cause": {

                "summary": summary,

                "file": "N/A",

                "function": "N/A",

                "evidence": [],

                "confidence": "INSUFFICIENT",

            },



            "evidence": [],



            "confidence": "INSUFFICIENT",



            "proposed_fix": "No patch proposed.",



            "proposed_patch": None,



            "log": tool_log,

        }
# ========================================================# SAFE RESPONSE TEXT# ========================================================
    @staticmethod

    def _safe_response_text(

        response: Any,

    ) -> str:



        try:



            return (

                getattr(

                    response,

                    "text",

                    "",

                )

                or ""

            )



        except Exception as exc:



            return (

                f"<unable to read response text: "

                f"{exc}>"

            )
# ========================================================# SAFE TOOL RESPONSE# ========================================================
    @staticmethod

    def _safe_tool_response(

        result: Any,

    ) -> Dict[str, Any]:



        if isinstance(

            result,

            dict,

        ):



            return result



        if isinstance(

            result,

            list,

        ):



            return {

                "success": True,

                "items": result,

            }



        return {

            "success": True,

            "result": str(result),

        }
# ========================================================# ERROR HANDLING# ========================================================
    @staticmethod

    def _handle_error(

        exc: Exception,

        tool_log: List[str],

        repo_name: str = "",

        bug_report: Any = None,

    ) -> Dict[str, Any]:



        message = str(exc)



        lower = message.lower()



        if (

            "quota" in lower

            or "resource exhausted" in lower

            or "429" in lower

        ):



            error_type = "quota_exceeded"



        elif (

            "api key" in lower

            or "authentication" in lower

            or "permission" in lower

            or "401" in lower

            or "403" in lower

        ):



            error_type = "authentication_error"



        elif (

            "timeout" in lower

            or "timed out" in lower

        ):



            error_type = "timeout"



        else:



            error_type = "provider_error"



        print(

            "[DEVGUARD][PROVIDER_ERROR] "

            f"type={error_type} "

            f"message={message}",

            flush=True,

        )



        return GeminiProvider._error_result(

            error_type,

            message,

            repo_name,

            bug_report,

            tool_log,

        )
# ========================================================# ERROR RESULT# ========================================================
    @staticmethod

    def _error_result(

        error_type: str,

        message: str,

        repo_name: str = "",

        bug_report: Any = None,

        tool_log: Optional[List[str]] = None,

    ) -> Dict[str, Any]:



        return {

            "success": False,



            "status": "PROVIDER_ERROR",



            "provider": "gemini",



            "error_type": error_type,



            "message": message,



            "repository": repo_name,



            "bug_report": bug_report,



            "affected_file": "N/A",



            "affected_function": "N/A",



            "root_cause": {

                "summary": "Gemini provider failed.",

                "file": "N/A",

                "function": "N/A",

                "evidence": [],

                "confidence": "INSUFFICIENT",

            },



            "evidence": [],



            "confidence": "INSUFFICIENT",



            "proposed_fix": "No patch proposed.",



            "proposed_patch": None,



            "log": tool_log or [],

        }