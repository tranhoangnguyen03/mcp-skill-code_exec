## Example

### Python usage

```python
import mcp_tools.bamboo_hr as bamboo_hr

all_employees = bamboo_hr.list_employees()
active_employees = bamboo_hr.list_employees(status="Active")
```

### Output (example)

```python
[
    {
        "id": 101,
        "name": "Alice Chen",
        "dept": "Engineering",
        "role": "Software Engineer",
        "status": "Active",
        "hire_date": "2026-01-03",
        "manager": "Jordan Lee",
        "slack_id": "U_ALICE",
        "manager_slack_id": "U_JORDAN",
    },
    {
        "id": 102,
        "name": "Ben Davis",
        "dept": "People Ops",
        "role": "HR Generalist",
        "status": "Active",
        "hire_date": "2025-08-11",
        "manager": "Riley Kim",
        "slack_id": "U_BEN",
        "manager_slack_id": "U_RILEY",
    },
]
```
