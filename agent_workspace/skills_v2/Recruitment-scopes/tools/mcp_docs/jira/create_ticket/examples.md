# Examples: jira.create_ticket

```python
import mcp_tools.jira as jira

ticket_id = jira.create_ticket(
    project="RECR",
    summary="Schedule interviews: candidate@example.com (Backend Engineer)",
    priority="High",
)
print(ticket_id)
```

