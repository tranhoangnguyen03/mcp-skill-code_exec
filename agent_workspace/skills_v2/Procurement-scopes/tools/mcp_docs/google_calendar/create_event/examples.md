# Examples: google_calendar.create_event

```python
import mcp_tools.google_calendar as gcal

event = gcal.create_event(
    email="requester@company.com",
    title="Vendor onboarding kickoff",
    start_time="2026-01-20T15:00:00",
    end_time="2026-01-20T15:30:00",
)
print(event["id"])
```

