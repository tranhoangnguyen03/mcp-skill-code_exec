## Example

### Python usage

```python
import mcp_tools.bamboo_hr as bamboo_hr

employees = bamboo_hr.get_probation_checkins(days_since_hire=90, window_days=7)
```

### Output (example)

```python
[
    {
        "id": 104,
        "name": "Devin Patel",
        "dept": "Engineering",
        "role": "QA Engineer",
        "status": "Active",
        "hire_date": "2025-10-16",
        "manager": "Jordan Lee",
        "slack_id": "U_DEVIN",
        "manager_slack_id": "U_JORDAN",
    }
]
```
