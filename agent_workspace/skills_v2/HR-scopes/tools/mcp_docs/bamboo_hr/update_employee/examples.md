## Example

### Python usage

```python
import mcp_tools.bamboo_hr as bamboo_hr

updated = bamboo_hr.update_employee(employee_id=101, updates={"role": "Staff Engineer"})
```

### Output (example)

```python
{
    "id": 101,
    "name": "Alice Chen",
    "dept": "Engineering",
    "role": "Staff Engineer",
    "status": "Active",
    "hire_date": "2026-01-03",
    "manager": "Jordan Lee",
    "slack_id": "U_ALICE",
    "manager_slack_id": "U_JORDAN",
}
```
