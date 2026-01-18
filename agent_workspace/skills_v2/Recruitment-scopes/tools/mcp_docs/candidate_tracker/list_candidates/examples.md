# Examples: candidate_tracker.list_candidates

```python
import mcp_tools.candidate_tracker as tracker

# List all candidates
all_cand = tracker.list_candidates()

# List candidates in a specific stage
tech_cand = tracker.list_candidates(stage="Technical")

# List candidates with a specific status
hired = tracker.list_candidates(status="Hired")
```
