# Custom Script Guidelines

> **When this document applies**: You are generating a one-off automation script because no pre-written skill matches the user's request. Follow these guidelines to produce minimal, correct, executable Python code.

---

## Core Principles

### 1. Minimalism
Implement **only** what the user asked for.
- Do not add extra steps, related workflows, or "nice-to-have" features
- If the user asks to "DM new hires a link," do not also create tickets or schedule meetings
- When in doubt, do less

### 2. Defensive Coding
Validate tool outputs and handle edge cases gracefully.
- Check for empty results before iterating (e.g., `if not employees: print("No employees found.")`)
- Wrap tool calls that might fail in appropriate error handling
- Print meaningful messages when data is missing or unexpected

### 3. Clarity
Print progress lines for each logical step.
- Users should see what the script is doing as it runs
- Example: `print(f"Found {len(hires)} new hires for today.")`
- End with a summary of actions taken

### 4. Determinism
When multiple items could match, select the best one explicitly.
- Prefer exact matches over partial matches
- If selecting from multiple candidates, print which one was chosen and why
- Example: `print(f"Selected employee: {employee['name']} (exact match)")`

### 5. Multi-turn Continuation
If the plan requires lookahead, signal the agent to continue by printing specific markers.
- **`CONTINUE_FACT: <fact>`**: Use this when you have discovered a piece of information needed for the next step.
- **`CONTINUE_WORKFLOW: <reason>`**: Use this to explicitly tell the agent to perform another codegen-execute cycle.
- Example: `print(f"CONTINUE_FACT: Davis domain is {domain}")`

### 6. Compliance
Use only the documented `mcp_tools` with correct signatures.
- Call tools using standard Python function syntax (positional or keyword arguments)
- Always provide required parameters
- Refer to the tool contracts provided in context for exact signatures

---

## Output Requirements

**Return ONLY a single Python code block.**

- No markdown explanations before or after
- No multiple code blocks
- The code must be immediately executable

---

## Code Structure Template

```python
# 1. Import tools (already available in execution context)
# from mcp_tools import bamboo_hr, slack, jira, etc.

# 2. Fetch required data
print("Step 1: Fetching data...")
data = some_tool.get_data(...)

# 3. Validate results
if not data:
    print("No data found. Exiting.")
else:
    # 4. Process and execute actions
    for item in data:
        print(f"Processing: {item['name']}")
        # ... perform action ...

    # 5. Print summary
    print(f"Done. Processed {len(data)} items.")
```

---

## Common Patterns

**Querying and listing:**
```python
employees = bamboo_hr.list_employees()
print(f"Found {len(employees)} employees.")
for emp in employees:
    print(f"  - {emp['name']} ({emp['department']})")
```

**Searching with fallback:**
```python
results = bamboo_hr.search_employees(query="Chen")
if not results:
    print("No employees matched the search.")
else:
    print(f"Found {len(results)} matches.")
```

**Sending notifications:**
```python
slack.send_message(channel="#general", text="Hello from automation!")
print("Message sent to #general.")
```

---

## Anti-Patterns to Avoid

- **Over-engineering**: Don't add error handling for impossible cases
- **Scope creep**: Don't add related actions the user didn't request
- **Silent failures**: Always print when something unexpected happens
- **Hardcoded values**: Use data from tool responses, not assumptions
