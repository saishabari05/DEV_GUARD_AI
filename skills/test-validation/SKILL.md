# Test Validation Skill

## Overview
This skill defines the rigorous, tool-authoritative process DevGuard AI follows to validate proposed bug fixes.

## Core Principle
Tool output is authoritative. LLM claims or self-reported success do NOT constitute test evidence.

## Validation Workflow
1. **Pre-Fix Test Execution**: Run test suite before patching. Confirm initial failing state (`FAILED_BEFORE_FIX`).
2. **Apply Patch**: Modify target file with proposed fix (`PATCH_APPLIED`).
3. **Post-Fix Test Execution**: Run targeted test suite. Inspect exit code and stdout/stderr (`VALIDATION_FAILED` if non-zero exit code).
4. **Regression Verification**: Run full repository test suite to ensure no collateral test failures occurred.
5. **Reversion on Failure**: If any post-patch tests fail, immediately revert patch using `revert_patch`.

## Validation States
- **NOT_RUN**: Tests have not been executed.
- **FAILED_BEFORE_FIX**: Initial tests confirmed reproduction of reported bug.
- **PATCH_APPLIED**: Fix has been written to disk but not yet verified by test suite.
- **VALIDATION_FAILED**: Post-fix test suite returned exit code != 0.
- **FIX_VERIFIED**: Post-fix test suite passed (exit code 0) with zero failing tests.
- **REGRESSION_DETECTED**: Pre-existing passing tests failed after patch application.

Final status `FIX_VERIFIED` requires empirical test pass confirmation.
