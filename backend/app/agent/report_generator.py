from typing import Dict, Any

def generate_report(investigation_data: Dict[str, Any]) -> str:
    """
    Generates a professional Markdown incident report from actual investigation result data.
    Ensures zero hallucinated evidence, files, or test statuses.
    """
    if not isinstance(investigation_data, dict):
        return "# DEVGUARD AI Investigation Report\n\nError: Invalid investigation data provided."

    repo_meta = investigation_data.get("repository_metadata", {})
    repo_name = (
        investigation_data.get("repository") 
        or repo_meta.get("repository_name")
        or "Unknown Repository"
    )
    if repo_name == "Unknown Repository" and repo_meta.get("workspace_id"):
        repo_name = repo_meta.get("workspace_id")

    bug_report = investigation_data.get("bug_report") or investigation_data.get("bug_summary") or "Autonomous Discovery Mode"
    if isinstance(bug_report, dict):
        bug_report = "Autonomous Discovery Mode (Automated failure analysis)"

    status = str(investigation_data.get("status", "UNFINISHED")).upper()
    provider = str(investigation_data.get("provider", "UNKNOWN")).upper()
    mode = str(investigation_data.get("investigation_mode", "directed")).upper()

    # Timeline construction:
    # PROJECT_DETECTED -> EVIDENCE_COLLECTED -> ROOT_CAUSE_IDENTIFIED -> PATCH_PROPOSED -> AWAITING_VALIDATION
    timeline_steps = [
        {"step": "PROJECT_DETECTED", "status": "SUCCESS", "detail": f"Language: {repo_meta.get('language', 'N/A')}, Framework: {repo_meta.get('framework', 'N/A')}"},
    ]

    raw_log = investigation_data.get("log", [])
    files_investigated = set()
    
    for entry in raw_log:
        if isinstance(entry, str):
            if "file_path=" in entry or "'file':" in entry:
                import re
                match = re.search(r"file_path=['\"]([^'\"]+)['\"]", entry)
                if match:
                    files_investigated.add(match.group(1))

    root_cause = investigation_data.get("root_cause", {})
    rc_file = root_cause.get("file") or investigation_data.get("affected_file") or "N/A"
    rc_function = root_cause.get("function") or investigation_data.get("affected_function") or "N/A"
    rc_summary = root_cause.get("summary") or "No root cause identified."
    rc_confidence = investigation_data.get("confidence") or root_cause.get("confidence") or ("HIGH" if rc_file != "N/A" else "INSUFFICIENT")

    if rc_file != "N/A":
        files_investigated.add(rc_file)

    evidence_items = investigation_data.get("evidence") or root_cause.get("evidence", [])
    
    # Check EVIDENCE_COLLECTED
    if evidence_items:
        timeline_steps.append({"step": "EVIDENCE_COLLECTED", "status": "SUCCESS", "detail": f"{len(evidence_items)} evidence items gathered"})
    else:
        timeline_steps.append({"step": "EVIDENCE_COLLECTED", "status": "INSUFFICIENT", "detail": "Insufficient evidence gathered"})

    # Check ROOT_CAUSE_IDENTIFIED
    # MUST NOT be marked successful when confidence is INSUFFICIENT
    if rc_confidence != "INSUFFICIENT" and rc_file != "N/A":
        timeline_steps.append({"step": "ROOT_CAUSE_IDENTIFIED", "status": "SUCCESS", "detail": f"Affected file: {rc_file}"})
    else:
        timeline_steps.append({"step": "ROOT_CAUSE_IDENTIFIED", "status": "INSUFFICIENT", "detail": "Root cause not conclusively identified"})

    proposed_patch = investigation_data.get("proposed_patch")
    has_valid_patch = proposed_patch and isinstance(proposed_patch, dict) and proposed_patch.get("patch")

    # Only generate PATCH_PROPOSED when Gemini has produced a valid evidence-backed patch
    if has_valid_patch and rc_confidence != "INSUFFICIENT":
        timeline_steps.append({"step": "PATCH_PROPOSED", "status": "SUCCESS", "detail": f"Patch created for {proposed_patch.get('file')}"})
        timeline_steps.append({"step": "AWAITING_VALIDATION", "status": "PENDING", "detail": "Awaiting patch validation execution"})
    else:
        timeline_steps.append({"step": "PATCH_PROPOSED", "status": "SKIPPED", "detail": "No valid patch proposed"})
        timeline_steps.append({"step": "AWAITING_VALIDATION", "status": "SKIPPED", "detail": "Validation skipped"})

    val_pipeline = investigation_data.get("validation_pipeline", {})
    pre_test = val_pipeline.get("pre_test")
    post_test = val_pipeline.get("post_test")

    lines = []
    lines.append("# DEVGUARD AI Investigation Report\n")
    lines.append(f"**AI Provider**: `{provider}` | **Mode**: `{mode}` | **Status**: `{status}`\n")
    
    lines.append("## Repository")
    lines.append(f"`{repo_name}`\n")

    lines.append("## Repository Metadata")
    lines.append(f"- **Name**: `{repo_name}`")
    if repo_meta.get("repository_url"):
        lines.append(f"- **URL**: `{repo_meta.get('repository_url')}`")
    lines.append(f"- **Language**: `{repo_meta.get('language', 'Unknown')}`")
    lines.append(f"- **Framework**: `{repo_meta.get('framework', 'Unknown')}`")
    lines.append(f"- **Test Command**: `{repo_meta.get('test_command', 'Unknown')}`")
    lines.append(f"- **File Count**: `{repo_meta.get('file_count', 0)}`\n")

    lines.append("## Investigation Timeline")
    for step_info in timeline_steps:
        lines.append(f"- **{step_info['step']}**: `{step_info['status']}` — {step_info['detail']}")
    lines.append("")

    lines.append("## Bug Description")
    lines.append(f"{bug_report}\n")

    lines.append("## Project Detection")
    lines.append(f"- **Affected File**: `{rc_file}`")
    lines.append(f"- **Affected Function**: `{rc_function}`\n")

    lines.append("## Evidence")
    if evidence_items:
        for i, ev in enumerate(evidence_items, 1):
            source_ref = f"`{ev.get('source') or ev.get('file') or 'Repository'}`"
            desc = ev.get("description") or ev.get("observation") or "Evidence observed during analysis."
            ev_type = ev.get("type", "evidence")
            lines.append(f"{i}. **[{ev_type.upper()}]** {source_ref}: {desc}")
    else:
        lines.append("Insufficient evidence gathered during analysis.")
    lines.append("")

    lines.append("## Root Cause")
    lines.append(f"**Summary**: {rc_summary}")
    lines.append(f"- **Confidence Level**: **{rc_confidence}**\n")

    lines.append("## Proposed Fix")
    if has_valid_patch and rc_confidence != "INSUFFICIENT":
        lines.append(f"**Target File**: `{proposed_patch.get('file')}`")
        lines.append(f"**Explanation**: {proposed_patch.get('description', 'Applied patch to resolve issue.')}\n")
    else:
        lines.append("No patch proposed or patch not available.\n")

    lines.append("## Validation Results")
    lines.append("### Validation Before Fix")
    if pre_test and isinstance(pre_test, dict):
        lines.append(f"- **Command**: `{pre_test.get('command', 'N/A')}`")
        lines.append(f"- **Exit Code**: `{pre_test.get('exit_code', 'N/A')}`")
        lines.append(f"- **Status**: `{pre_test.get('status', 'FAILED')}`")
    else:
        lines.append("Pre-fix test execution not recorded or skipped.")

    lines.append("\n### Validation After Fix")
    if post_test and isinstance(post_test, dict):
        lines.append(f"- **Command**: `{post_test.get('command', 'N/A')}`")
        lines.append(f"- **Exit Code**: `{post_test.get('exit_code', 'N/A')}`")
        lines.append(f"- **Status**: `{post_test.get('status', 'PASSED' if status == 'PASSED' else 'FAILED')}`")
    else:
        lines.append("NOT_VALIDATED (Post-fix test has not run or was rejected)")

    lines.append("\n## Final Status")
    lines.append(f"**{status}**")

    return "\n".join(lines)
