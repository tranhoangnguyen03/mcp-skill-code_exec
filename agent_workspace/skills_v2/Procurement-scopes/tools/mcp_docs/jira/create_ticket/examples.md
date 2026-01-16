# Examples: jira.create_ticket

```python
import mcp_tools.jira as jira

ticket_id = jira.create_ticket(
    project="PROC",
    summary="Purchase request: Laptop for Engineering ($2500)",
    priority="High",
)
print(ticket_id)
```

