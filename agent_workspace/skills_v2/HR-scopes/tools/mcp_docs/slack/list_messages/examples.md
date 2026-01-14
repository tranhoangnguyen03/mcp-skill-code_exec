## Example

### Python usage

```python
import mcp_tools.slack as slack

messages = slack.list_messages(channel="dm")
```

### Output (example)

```python
[
    {
        "channel": "dm",
        "user_id": "U_ALICE",
        "text": "Welcome to the team.",
    }
]
```
