## Example

### Python usage

```python
import mcp_tools.jira as jira

tickets = jira.search_tickets(project="IT", status="Open")
```

### Output (example)

```python
[
    {
        "id": "IT-101",
        "project": "IT",
        "summary": "Laptop setup for Alice Chen",
        "priority": "High",
        "status": "Open",
    }
]
```
