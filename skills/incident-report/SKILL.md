# Incident Report Skill

## Overview
This skill defines the structure and requirements for generating developer-ready incident and investigation reports from DevGuard AI execution data.

## Standard Report Sections
Every investigation report must contain the following sections:
1. **Executive Summary**: High-level overview of the incident investigation and resolution status.
2. **Bug Description**: Reported problem summary and original user description.
3. **Repository**: Name and path of the target code repository.
4. **Investigation Timeline**: Chronological log of investigation stages, tool executions, and findings.
5. **Files Investigated**: Exact list of files searched or inspected during the investigation.
6. **Evidence**: Concrete code observations, test failures, or diff excerpts collected.
7. **Root Cause**: Detailed root cause breakdown including Affected File, Affected Function, Description, and Confidence.
8. **Proposed Fix**: Description of proposed code changes and patch contents.
9. **Applied Fix**: Details of files modified when patch was applied.
10. **Validation Results**: Pre-patch and post-patch test execution status and output logs.
11. **Regression Results**: Verification status of full repository test suite.
12. **Final Status**: Definitive state (`FIX_VERIFIED`, `FIX_REJECTED`, `INSUFFICIENT_EVIDENCE`).

## Integrity Rules
- Report content must strictly derive from empirical investigation data.
- Do not list unvisited files under `Files Investigated`.
- Do not claim tests passed or fix verified unless verified by tool output logs.
- If evidence or confidence is insufficient, accurately convey uncertainty.
