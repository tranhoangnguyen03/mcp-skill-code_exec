# Examples: candidate_tracker.add_interview_log

```python
import mcp_tools.candidate_tracker as tracker

# Log a passed screening interview
tracker.add_interview_log(
    email="cand_4",
    stage="Screening",
    interviewer="Dana Patel",
    outcome="Passed"
)

# Log a technical interview with feedback
tracker.add_interview_log(
    email="sarah.j@example.com",
    stage="Technical",
    interviewer="Charlie Davis",
    outcome="Strong Hire",
    date_str="2026-01-15"
)
```
