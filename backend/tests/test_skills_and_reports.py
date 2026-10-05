import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.agent.skill_loader import load_skill, load_all_skills
from app.agent.report_generator import generate_report

def test_load_valid_skills():
    bug_inv = load_skill("bug-investigation")
    assert "Bug Investigation Skill" in bug_inv
    
    rca = load_skill("root-cause-analysis")
    assert "Root Cause Analysis Skill" in rca

    val = load_skill("test-validation")
    assert "Test Validation Skill" in val

    rep = load_skill("incident-report")
    assert "Incident Report Skill" in rep

def test_reject_unknown_skill():
    with pytest.raises(ValueError, match="Unknown or unapproved skill"):
        load_skill("non-existent-skill")

def test_reject_path_traversal():
    with pytest.raises(ValueError):
        load_skill("../bug-investigation")

def test_reject_invalid_input():
    with pytest.raises(ValueError):
        load_skill("")

def test_load_all_skills():
    skills = load_all_skills()
    assert len(skills) == 4
    assert "bug-investigation" in skills
    assert "root-cause-analysis" in skills

def test_report_generator_sections():
    sample_data = {
        "repository": "auth_bug",
        "bug_report": "Users cannot log in when using uppercase emails.",
        "status": "PASSED",
        "root_cause": {
            "file": "app/auth.py",
            "function": "authenticate_user",
            "summary": "Email address was not normalized to lowercase.",
            "confidence": "HIGH",
            "evidence": [{"source": "app/auth.py", "description": "Lookup uses raw email."}]
        },
        "proposed_patch": {
            "file": "app/auth.py",
            "description": "Normalize email using .lower()",
            "patch": "fix content"
        },
        "validation_pipeline": {
            "pre_test": {"status": "failed", "passed": 3, "failed": 1},
            "post_test": {"status": "passed", "passed": 4, "failed": 0}
        },
        "log": ["Mock requested: tool_run_tests", "Mock requested: tool_read_repository_file file_path='app/auth.py'"]
    }
    
    report = generate_report(sample_data)
    assert "# DEVGUARD AI Investigation Report" in report
    assert "## Bug Description" in report
    assert "## Repository" in report
    assert "## Project Detection" in report
    assert "## Evidence" in report
    assert "## Root Cause" in report
    assert "## Proposed Fix" in report
    assert "## Validation Results" in report
    assert "## Final Status" in report
    assert "`app/auth.py`" in report
    assert "HIGH" in report

