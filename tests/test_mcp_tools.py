from agent_workspace.mcp_tools import bamboo_hr, jira, slack


def test_bamboo_hr_get_employee_and_update():
    e = bamboo_hr.get_employee(101)
    assert e is not None
    assert e["name"] == "Alice Chen"

    updated = bamboo_hr.update_employee(101, {"role": "Staff Engineer"})
    assert updated["role"] == "Staff Engineer"

    updated2 = bamboo_hr.update_employee({"employee_id": 101, "updates": {"role": "Principal Engineer"}})
    assert updated2["role"] == "Principal Engineer"


def test_bamboo_hr_search_accepts_mcp_payload():
    matches = bamboo_hr.search_employees({"query": "Davis"})
    assert any(m["name"] == "Charlie Davis" for m in matches)

def test_jira_create_ticket_and_get_ticket():
    tid = jira.create_ticket(project="IT", summary="Test", priority="High")
    t = jira.get_ticket(tid)
    assert t is not None
    assert t["project"] == "IT"

    tid2 = jira.create_ticket({"project": "IT", "summary": "Test2", "priority": "Low"})
    t2 = jira.get_ticket({"ticket_id": tid2})
    assert t2 is not None
    assert t2["priority"] == "Low"


def test_slack_send_and_list_messages():
    slack.send_dm("U_TEST", "hello")
    msgs = slack.list_messages()
    assert any(m["user_id"] == "U_TEST" and m["text"] == "hello" for m in msgs)

    slack.send_dm({"user_id": "U_TEST2", "message": "hello2"})
    msgs2 = slack.list_messages({"channel": "dm"})
    assert any(m["user_id"] == "U_TEST2" and m["text"] == "hello2" for m in msgs2)
