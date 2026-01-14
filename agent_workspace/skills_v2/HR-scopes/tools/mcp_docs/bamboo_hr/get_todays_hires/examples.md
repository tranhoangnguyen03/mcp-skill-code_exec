## Example

### Python usage

```python
import mcp_tools.bamboo_hr as bamboo_hr

hires = bamboo_hr.get_todays_hires()
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
        "hire_date": "2026-01-14",
        "manager": "Jordan Lee",
        "slack_id": "U_ALICE",
        "manager_slack_id": "U_JORDAN",
    }
]
```
