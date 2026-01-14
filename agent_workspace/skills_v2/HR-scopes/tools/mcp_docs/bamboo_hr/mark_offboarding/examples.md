## Example

### Python usage

```python
import mcp_tools.bamboo_hr as bamboo_hr

updated = bamboo_hr.mark_offboarding(employee_id=101, effective_date="2026-02-01")
```

### Output (example)

```python
{
    "id": 101,
    "name": "Alice Chen",
    "dept": "Engineering",
    "role": "Software Engineer",
    "status": "Offboarding (2026-02-01)",
    "hire_date": "2026-01-03",
    "manager": "Jordan Lee",
    "slack_id": "U_ALICE",
    "manager_slack_id": "U_JORDAN",
}
```
