import pytest
import io
import zipfile
from app.agent.provider_factory import get_llm_provider
from app.agent.providers.mock import MockProvider
from app.agent.providers.gemini import GeminiProvider
from app.agent.autonomous_pipeline import run_autonomous_investigation
from app.agent.investigator import investigate
from app.repository.manager import RepositoryManager

def test_provider_factory_mock(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    provider = get_llm_provider()
    assert isinstance(provider, MockProvider)

def test_provider_factory_gemini(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    provider = get_llm_provider()
    assert isinstance(provider, GeminiProvider)
    
def test_mock_investigation():
    provider = MockProvider()
    
    def tool_search_repository(query: str):
        return {"success": True, "query": query, "matches": []}
    def tool_read_repository_file(file_path: str):
        return {"success": True, "content": "mock content"}
    def tool_run_tests():
        return {"success": True, "status": "failed", "exit_code": 1}
        
    tools = [tool_search_repository, tool_read_repository_file, tool_run_tests]
    
    result = provider.investigate("/mock/repo", "auth_bug", "mock bug report", tools)
    
    assert result["success"] is True
    assert result["provider"] == "mock"
    assert result["status"] == "ROOT_CAUSE_IDENTIFIED"
    assert "log" in result

def test_autonomous_investigation_pipeline():
    # Setup isolated test repository in memory / workspace
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("app/__init__.py", "# init")
        zf.writestr("app/auth.py", "def authenticate_user(email):\n    return email\n")
        zf.writestr("tests/test_auth.py", "def test_failing():\n    assert False, 'Authentication error expected'\n")
    
    ingest_res = RepositoryManager.ingest_zip_repo(zip_buf.getvalue())
    ws_id = ingest_res["workspace_id"]
    from app.repository.workspace import resolve_workspace_path
    ws_path = resolve_workspace_path(ws_id)

    auto_res = run_autonomous_investigation(ws_path, ws_id)
    assert "metadata" in auto_res
    assert auto_res["metadata"]["language"] == "Python"
    assert auto_res["metadata"]["test_command"] == "pytest"
    
    ctx = auto_res["evidence_context"]
    assert ctx["test_result"]["exit_code"] != 0
    assert "app/auth.py" in ctx["source_code_inspected"] or "tests/test_auth.py" in ctx["source_code_inspected"]
    
    # Assert step logs
    logs_str = "\n".join(auto_res["logs"])
    assert "[DISCOVERY]" in logs_str
    assert "[TEST_DISCOVERY]" in logs_str
    assert "[TEST_EXECUTION]" in logs_str
    assert "[FAILURE_ANALYSIS]" in logs_str
    assert "[SOURCE_INSPECTION]" in logs_str
    assert "[GEMINI_ANALYSIS]" in logs_str


def test_evidence_budget_prioritizes_failures_and_skips_documentation():
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        zf.writestr("README.md", "This should not be needed to diagnose the failure.")
        zf.writestr("WORKSHOP.md", "General workshop notes.")
        zf.writestr("app/orders.py", "def total():\n    return 1\n")
        zf.writestr(
            "tests/test_orders.py",
            "from app.orders import total\n\n"
            "def test_total():\n"
            "    assert total() == 2\n",
        )

    ingest_res = RepositoryManager.ingest_zip_repo(zip_buf.getvalue())
    from app.repository.workspace import resolve_workspace_path
    ws_path = resolve_workspace_path(ingest_res["workspace_id"])

    auto_res = run_autonomous_investigation(ws_path, ingest_res["workspace_id"])
    ctx = auto_res["evidence_context"]
    logs = "\n".join(auto_res["logs"])

    assert "tests/test_orders.py::test_total" in ctx["test_result"]["failing_tests"]
    assert ctx["test_result"]["assertion_details"]["actual"] == "1"
    assert ctx["test_result"]["assertion_details"]["expected"] == "2"
    assert "tests/test_orders.py" in ctx["source_code_inspected"]
    assert "README.md" not in ctx["source_code_inspected"]
    assert "WORKSHOP.md" not in ctx["source_code_inspected"]
    assert "[DEVGUARD][EVIDENCE] SKIPPED LOW PRIORITY DOC: README.md" in logs
    assert "[DEVGUARD][EVIDENCE] SKIPPED LOW PRIORITY DOC: WORKSHOP.md" in logs
    assert ctx["evidence_budget"]["documentation_reads"] == 0
