import functools
import os
from typing import Dict, Any, Callable

from .provider_factory import get_llm_provider

from ..tools.repository import (
    search_repository,
    read_repository_file,
)

from ..tools.git import (
    get_git_history,
    get_git_diff,
)

from ..tools.testing import run_tests

from .autonomous_pipeline import run_autonomous_investigation
from ..repository.detector import detect_repository_metadata


def _build_evidence_read_tool(
    repo_path: str,
    evidence_context: Dict[str, Any],
    bug_report: str,
) -> Callable:
    """Wrap file reads with a small evidence budget and a duplicate-read cache."""
    inspected = evidence_context.get("source_code_inspected", {})
    priority = evidence_context.get("evidence_priority", {})
    high_priority = set(priority.get("high", []))
    documentation = set(priority.get("low_skipped", []))
    explicit_docs = {
        path for path in documentation
        if bug_report and os.path.basename(path).lower() in bug_report.lower()
    }
    cache: Dict[str, Dict[str, Any]] = {}

    @functools.wraps(read_repository_file)
    def read_with_budget(repository_path: str, file_path: str) -> Dict[str, Any]:
        normalized = str(file_path).replace("\\", "/").lstrip("./")
        if normalized in cache:
            print(
                f"[DEVGUARD][EVIDENCE] CACHED: {normalized} (duplicate read avoided)",
                flush=True,
            )
            return cache[normalized]

        if normalized in documentation and normalized not in explicit_docs:
            unread_high = high_priority - set(inspected)
            if unread_high:
                message = (
                    f"[DEVGUARD][EVIDENCE] SKIPPED LOW PRIORITY DOC: {normalized} "
                    f"(relevant evidence remains: {sorted(unread_high)})"
                )
                print(message, flush=True)
                return {"success": False, "error": message, "skipped": True}

        result = read_repository_file(repository_path, normalized)
        cache[normalized] = result
        return result

    return read_with_budget


def investigate(
    repo_path: str,
    repo_identifier: str,
    bug_report: str = None
) -> dict:

    print("[DEVGUARD][INVESTIGATE] Starting investigation", flush=True)
    print(f"[DEVGUARD][REPO_PATH] {repo_path}", flush=True)
    print(f"[DEVGUARD][REPO_IDENTIFIER] {repo_identifier}", flush=True)

    # ---------------------------------------------------------
    # 1. Load LLM provider
    # ---------------------------------------------------------

    provider = get_llm_provider()

    print(
        f"[DEVGUARD][PROVIDER_CLASS] "
        f"{provider.__class__.__module__}.{provider.__class__.__name__}",
        flush=True
    )

    # ---------------------------------------------------------
    # 2. Register deterministic tools
    # ---------------------------------------------------------

    # ---------------------------------------------------------
    # 3. Determine investigation mode
    # ---------------------------------------------------------

    mode = (
        "directed"
        if bug_report and bug_report.strip()
        else "autonomous"
    )

    print(
        f"[DEVGUARD][MODE] Investigation mode = {mode}",
        flush=True
    )

    # ---------------------------------------------------------
    # 4. Detect repository metadata
    # ---------------------------------------------------------

    metadata = detect_repository_metadata(repo_path)

    print(
        f"[DEVGUARD][METADATA] {metadata}",
        flush=True
    )

    # ---------------------------------------------------------
    # 5. Run deterministic autonomous discovery
    # ---------------------------------------------------------

    auto_res = run_autonomous_investigation(
        repo_path=repo_path,
        repo_identifier=repo_identifier,
        bug_report=bug_report,
    )

    evidence_ctx = auto_res["evidence_context"]

    evidence_ctx["investigation_mode"] = mode

    evidence_ctx["bug_report"] = (
        bug_report
        if mode == "directed"
        else None
    )

    tools = [
        search_repository,
        _build_evidence_read_tool(repo_path, evidence_ctx, bug_report or ""),
        get_git_history,
        get_git_diff,
        run_tests,
    ]

    repo_name = (
        auto_res["metadata"].get("repository_name")
        or repo_identifier
    )

    print(
        f"[DEVGUARD][DISCOVERY_COMPLETE] "
        f"Repository={repo_name}",
        flush=True
    )

    # ---------------------------------------------------------
    # 6. Send evidence to Gemini
    # ---------------------------------------------------------

    print(
        f"[DEVGUARD][GEMINI_INPUT] "
        f"Sending structured context to Gemini for repo={repo_name}",
        flush=True
    )

    print(
        "[DEVGUARD][PROVIDER_CALL] Calling provider.investigate()",
        flush=True
    )

    try:

        res = provider.investigate(
            repo_path,
            repo_name,
            evidence_ctx,
            tools
        )

        print(
            "[DEVGUARD][PROVIDER_RETURNED]",
            flush=True
        )

        print(
            f"[DEVGUARD][PROVIDER_STATUS] "
            f"{res.get('status')}",
            flush=True
        )

        print(
            f"[DEVGUARD][PROVIDER_CONFIDENCE] "
            f"{res.get('confidence')}",
            flush=True
        )

        print(
            f"[DEVGUARD][PROVIDER_AFFECTED_FILE] "
            f"{res.get('affected_file')}",
            flush=True
        )

    except Exception as exc:

        print(
            f"[DEVGUARD][PROVIDER_EXCEPTION] "
            f"{type(exc).__name__}: {exc}",
            flush=True
        )

        raise

    # ---------------------------------------------------------
    # 7. Combine logs
    # ---------------------------------------------------------

    combined_logs = (
        auto_res.get("logs", [])
        + res.get("log", [])
    )

    res["log"] = combined_logs

    # ---------------------------------------------------------
    # 8. Provider error
    # ---------------------------------------------------------

    if res.get("status") == "PROVIDER_ERROR":

        print(
            "[DEVGUARD][PROVIDER_ERROR] "
            "Provider returned an error",
            flush=True
        )

        return res

    # ---------------------------------------------------------
    # 9. Validate affected file
    # ---------------------------------------------------------

    existing_files = evidence_ctx.get(
        "existing_files_in_repo",
        []
    )

    aff_file = res.get("affected_file")

    if isinstance(aff_file, str):

        aff_file = (
            aff_file
            .replace("\\", "/")
            .lstrip("./")
        )

        res["affected_file"] = aff_file

    # IMPORTANT:
    # Normalize repository file paths as well.
    normalized_existing_files = {
        str(path)
        .replace("\\", "/")
        .lstrip("./")
        for path in existing_files
    }

    print(
        f"[DEVGUARD][FILE_VALIDATION] "
        f"Affected file={aff_file}",
        flush=True
    )

    print(
        f"[DEVGUARD][FILE_VALIDATION] "
        f"Existing files={len(normalized_existing_files)}",
        flush=True
    )

    if (
        aff_file
        and aff_file != "N/A"
        and aff_file not in normalized_existing_files
    ):

        print(
            f"[DEVGUARD][FILE_VALIDATION_FAILED] "
            f"{aff_file} not found in repository",
            flush=True
        )

        res["affected_file"] = "N/A"
        res["affected_function"] = "N/A"
        res["confidence"] = "INSUFFICIENT"
        res["status"] = "INSUFFICIENT_EVIDENCE"

        res.setdefault("evidence", [])

        if not res["evidence"]:

            deterministic = evidence_ctx.get(
                "deterministic_evidence",
                []
            )

            res["evidence"] = deterministic

        return res

    # ---------------------------------------------------------
    # 10. Handle insufficient evidence
    # ---------------------------------------------------------

    if res.get("confidence") == "INSUFFICIENT":

        print(
            "[DEVGUARD][INSUFFICIENT_EVIDENCE]",
            flush=True
        )

        res["status"] = "INSUFFICIENT_EVIDENCE"

        if not res.get("evidence"):

            deterministic = evidence_ctx.get(
                "deterministic_evidence",
                []
            )

            res["evidence"] = deterministic

    # ---------------------------------------------------------
    # 11. Final result
    # ---------------------------------------------------------

    print(
        f"[DEVGUARD][INVESTIGATION_COMPLETE] "
        f"status={res.get('status')} "
        f"confidence={res.get('confidence')} "
        f"affected_file={res.get('affected_file')}",
        flush=True
    )

    return res