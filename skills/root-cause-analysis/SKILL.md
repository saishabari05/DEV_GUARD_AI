# Root Cause Analysis Skill

## Overview
This skill defines the disciplined analysis process for identifying, documenting, and rating confidence in software bug root causes.

## Structured Root Cause Schema
Every root-cause analysis output must detail:
- **Affected File**: The exact repository-relative path to the file containing the bug.
- **Affected Function/Class**: The specific function, method, or class where the flaw resides.
- **Observed Behavior**: The actual flawed outcome produced by the current code.
- **Expected Behavior**: The correct outcome required by system specification or tests.
- **Root Cause**: A precise description of the underlying logic flaw or missing condition.
- **Supporting Evidence**: Explicit references to code snippets, failing test outputs, or runtime results.
- **Confidence**: Rationale-backed level (`HIGH`, `MEDIUM`, `LOW`, or `INSUFFICIENT`).

## Rules of Evidence
- Root-cause claims must be supported by empirical evidence from source files, test outputs, git history, or runtime execution.
- LLM assumptions or unverified guesses are NOT evidence.
- If available evidence is insufficient to determine the root cause, state: `Insufficient evidence to determine the root cause.` and set confidence to `INSUFFICIENT`.

## Confidence Rating Criteria
- **HIGH**: Multiple independent pieces of empirical evidence (e.g. failing test traceback + direct source code defect) confirm the root cause.
- **MEDIUM**: Evidence strongly indicates the cause, but additional reproduction or verification is desirable.
- **LOW**: Plausible hypothesis supported by limited or indirect evidence.
- **INSUFFICIENT**: Current evidence cannot support a reliable conclusion.
