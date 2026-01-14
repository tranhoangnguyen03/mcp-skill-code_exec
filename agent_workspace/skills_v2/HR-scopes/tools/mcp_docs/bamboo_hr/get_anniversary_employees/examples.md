## Example

### Python usage

```python
import mcp_tools.bamboo_hr as bamboo_hr

employees = bamboo_hr.get_anniversary_employees(days_ahead=7)
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
        "hire_date": "2024-01-21",
        "manager": "Jordan Lee",
        "slack_id": "U_ALICE",
        "manager_slack_id": "U_JORDAN",
    }
]
```
