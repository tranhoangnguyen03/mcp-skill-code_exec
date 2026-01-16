# Examples: google_calendar.create_event

```python
import mcp_tools.google_calendar as gcal

event = gcal.create_event(
    email="interviewer@company.com",
    title="Interview: candidate@example.com",
    start_time="2026-01-20T10:00:00",
    end_time="2026-01-20T11:00:00",
)
print(event["id"])
```

