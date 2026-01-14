## Example

### Python usage

```python
import mcp_tools.jira as jira

ticket = jira.get_ticket(ticket_id="IT-101")
```

### Output (example)

```python
{
    "id": "IT-101",
    "project": "IT",
    "summary": "Laptop setup for Alice Chen",
    "priority": "High",
    "status": "Open",
}
```
