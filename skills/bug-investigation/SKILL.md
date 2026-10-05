# Bug Investigation Skill

## Overview
This skill defines the autonomous procedure DevGuard AI uses to investigate software bug reports within a repository.

## Procedure
1. **Understand the Bug Report**: Carefully analyze the user report to identify symptoms, affected endpoints, or expected outputs.
2. **Identify Candidate Repository Areas**: Determine which modules, services, or test files likely touch the reported issue.
3. **Reproduce the Failure**: Execute the test suite deterministically before exploratory investigation.
4. **Collect Failure Evidence**: Capture failing test names, assertions, expected/actual values, tracebacks, and affected locations.
5. **Identify Candidate Repository Areas**: Prioritize failing tests, traceback/source files, and direct imports/functions.
6. **Read Relevant Source Files**: Examine only the highest-value executable evidence first.
7. **Search Repository**: Search for relevant symbols, route names, error messages, or keywords.
8. **Collect Evidence**: Document source code lines, failing assertions, or runtime logs that directly point to the issue.
8. **Identify Candidate Causes**: Formulate candidate explanations supported by evidence.
9. **Continue Investigation**: If evidence is insufficient or ambiguous, perform additional file inspections or queries. Do not assume the first matching file is the root cause.
10. **Produce Structured Result**: Output the evidence-backed investigation result with root cause details and proposed fix.

## Guidelines
- Always distinguish symptoms (e.g. failing API endpoint response) from root causes (e.g. invalid transformation function or wrong SQL filter).
- Verify candidate causes against actual source code before concluding investigation.
- Prefer executable evidence over documentation. Do not read README.md, WORKSHOP.md,
  or general documentation merely because it exists; read it only when relevant
  code and test evidence cannot resolve an ambiguity or the bug report explicitly
  references it.
- Avoid duplicate file reads and use the minimum number of tool calls needed for
  an evidence-backed conclusion.
