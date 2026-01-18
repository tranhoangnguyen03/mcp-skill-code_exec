from pathlib import Path
import sys
from contextlib import contextmanager

@contextmanager
def _sys_path(path: Path):
    p = str(path)
    sys.path.insert(0, p)
    try:
        yield
    finally:
        try:
            sys.path.remove(p)
        except ValueError:
            pass

def test_candidate_tracker_loads_fixtures():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"
    
    with _sys_path(v2_tools_root):
        from mcp_tools import candidate_tracker
        
        # Reset internal state for clean test
        candidate_tracker._CANDIDATES = []
        
        candidates = candidate_tracker.list_candidates()
        assert len(candidates) >= 5
        
        # Verify date token expansion worked
        cand1 = next(c for c in candidates if c["id"] == "cand_1")
        history = cand1["interview_history"][0]
        assert history["date"] != "${TODAY_MINUS_7}"
        # It should be a valid ISO date
        from datetime import date
        date.fromisoformat(history["date"])

def test_candidate_tracker_filters():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"
    
    with _sys_path(v2_tools_root):
        from mcp_tools import candidate_tracker
        
        # Filter by stage
        tech_cands = candidate_tracker.list_candidates(stage="Technical")
        assert all(c["stage"] == "Technical" for c in tech_cands)
        assert len(tech_cands) >= 2
        
        # Filter by status
        rejected = candidate_tracker.list_candidates(status="Rejected")
        assert len(rejected) == 1
        assert rejected[0]["name"] == "Linda Wu"

def test_candidate_tracker_search():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"
    
    with _sys_path(v2_tools_root):
        from mcp_tools import candidate_tracker
        
        # Search by skill
        react_devs = candidate_tracker.search_candidates("React")
        assert any(c["name"] == "Sarah Jenkins" for c in react_devs)
        
        # Search by role
        pm = candidate_tracker.search_candidates("Product Manager")
        assert pm[0]["name"] == "David Smith"

def test_candidate_tracker_updates():
    repo_root = Path(__file__).resolve().parents[1]
    v2_tools_root = repo_root / "agent_workspace" / "skills_v2" / "HR-scopes" / "tools"
    
    with _sys_path(v2_tools_root):
        from mcp_tools import candidate_tracker
        
        email = "sarah.j@example.com"
        candidate_tracker.update_candidate_stage(email, "On-site")
        
        cand = candidate_tracker.get_candidate(email)
        assert cand["stage"] == "On-site"
        
        candidate_tracker.add_interview_log(email, "On-site", "Jordan Lee", outcome="Passed")
        cand = candidate_tracker.get_candidate(email)
        assert len(cand["interview_history"]) == 2
        assert cand["interview_history"][1]["stage"] == "On-site"
        assert cand["interview_history"][1]["outcome"] == "Passed"
