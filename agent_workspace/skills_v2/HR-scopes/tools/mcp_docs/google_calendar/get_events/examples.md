## Get Calendar Events

List events for a specific user, optionally filtered by date.

### Example 1: List all events
```python
google_calendar.get_events(email="alice@company.com")
```

### Example 2: Filter by date
```python
google_calendar.get_events(email="alice@company.com", date="2023-12-25")
```
