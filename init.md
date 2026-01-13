To enact this, we need to build the **Agent Workspace**. This workspace needs three distinct layers:
1.  **`mcp_tools/`**: The raw API connections (Bamboo, Jira, Slack).
2.  **`skills/`**: The "Instruction Manuals" (`SKILL.md`) that teach the AI how to use those tools for specific jobs.
3.  **The Agent Logic**: A script that simulates the AI discovering the skill, reading the manual, and generating the solution code.

Here is the complete setup.

### Part 1: The File Structure
Imagine your project folder looks like this. I have designed this to match the "Progressive Disclosure" concept (the AI scans folders first, then reads files).

```text
agent_workspace/
│
├── mcp_tools/               <-- The Raw "API" Wrappers
│   ├── __init__.py
│   ├── bamboo_hr.py
│   ├── jira.py
│   └── slack.py
│
├── skills/                  <-- The "Skills" Directory
│   └── new_hire_onboarding/
│       └── SKILL.md         <-- The instruction manual for the AI
│
└── main_agent.py            <-- The AI Agent (Simulated)
```

---

### Part 2: The Assets (Python Code)

I have written a setup script below. You can copy and run this entire block in Python. It will **automatically create the folders and files** for you, and then simulate the agent running the onboarding process.

```python
import os
import sys
import time

# ==========================================
# SETUP: HELPER TO CREATE FOLDERS & FILES
# ==========================================
def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

print("🏗️  Building Agent Workspace...")

# ------------------------------------------
# 1. CREATE THE MOCK TOOLS (mcp_tools)
# These represent the 'drivers' for Bamboo, Jira, and Slack
# ------------------------------------------

# mcp_tools/bamboo_hr.py
create_file("mcp_tools/bamboo_hr.py", """
def get_todays_hires():
    # In reality, this would hit the BambooHR API
    return [
        {"id": 101, "name": "Alice Chen", "dept": "Engineering", "slack_id": "U_ALICE"},
        {"id": 102, "name": "Bob Smith", "dept": "Sales", "slack_id": "U_BOB"},
        {"id": 103, "name": "Charlie Davis", "dept": "Engineering", "slack_id": "U_CHARLIE"}
    ]
""")

# mcp_tools/jira.py
create_file("mcp_tools/jira.py", """
def create_ticket(project, summary, priority):
    # Mock Jira API call
    ticket_id = f"{project}-{hash(summary) % 1000}"
    print(f"   [Jira] Created ticket {ticket_id}: '{summary}' (Priority: {priority})")
    return ticket_id
""")

# mcp_tools/slack.py
create_file("mcp_tools/slack.py", """
def send_dm(user_id, message):
    # Mock Slack API call
    print(f"   [Slack] Sent DM to {user_id}: \\"{message}\\"")
""")

# Empty __init__.py to make it a package
create_file("mcp_tools/__init__.py", "")


# ------------------------------------------
# 2. CREATE THE SKILL DEFINITION (SKILL.md)
# This is what the AI reads to learn *how* to do the job.
# ------------------------------------------

skill_md_content = """
# Skill: Engineering Onboarding

## Description
This skill handles the onboarding process for new Engineering hires found in BambooHR. 
It ensures they have a Jira ticket for IT setup and receive a welcome message on Slack.

## Dependencies
- mcp_tools.bamboo_hr
- mcp_tools.jira
- mcp_tools.slack

## Logic Flow
1. Fetch today's hires from BambooHR.
2. Filter for employees where `dept` is 'Engineering'.
3. For each engineer:
    a. Create a Jira ticket (Project: IT, Priority: High).
    b. Send a Slack DM welcoming them.

## Code Example (Reference)
```python
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
# ... iterate and call functions ...
```
"""

create_file("skills/new_hire_onboarding/SKILL.md", skill_md_content)

print("✅ Workspace built successfully.\n")


# ==========================================
# 3. THE SIMULATION (The "Agent")
# ==========================================

class AI_Agent:
    def __init__(self):
        self.memory = []
    
    def scan_skills(self):
        """Simulates the AI looking at the file system to find capabilities."""
        print("🤖 AGENT: Scanning 'skills' directory...")
        skills = []
        for root, dirs, files in os.walk("skills"):
            if "SKILL.md" in files:
                skills.append(os.path.join(root, "SKILL.md"))
        return skills

    def read_skill(self, path):
        """Simulates the AI reading the instruction manual."""
        print(f"🤖 AGENT: Reading instructions from {path}...")
        with open(path, "r") as f:
            return f.read()

    def generate_and_execute_script(self, skill_content):
        """
        In a real scenario, the LLM writes this code based on the SKILL.md.
        Here, we simulate the LLM 'writing' the correct Python script.
        """
        print("🤖 AGENT: 'Writing' Python script based on SKILL.md...")
        time.sleep(1) # Thinking time
        
        # This is the code the "LLM" produces based on the SKILL.md instructions
        generated_code = """
print("⚡ EXECUTION ENV: Running Onboarding Script...")
import mcp_tools.bamboo_hr as bamboo
import mcp_tools.jira as jira
import mcp_tools.slack as slack

# 1. Fetch Data
hires = bamboo.get_todays_hires()
print(f"   -> Found {len(hires)} total new hires.")

# 2. Filter & Execute
for employee in hires:
    if employee['dept'] == 'Engineering':
        print(f"   -> Processing {employee['name']}...")
        
        # Create Ticket
        jira.create_ticket(
            project="IT", 
            summary=f"Laptop Setup for {employee['name']}", 
            priority="High"
        )
        
        # Send Message
        slack.send_dm(
            user_id=employee['slack_id'], 
            message="Welcome to the team! IT is setting up your laptop."
        )
print("⚡ EXECUTION ENV: Script Complete.")
"""
        # Execute the generated code
        print("🤖 AGENT: Executing the generated code...\n" + "="*40)
        exec(generated_code)
        print("="*40)

# --- RUN THE SCENARIO ---
if __name__ == "__main__":
    agent = AI_Agent()
    
    # Step 1: User Prompt
    print("User: 'Run the Monday morning onboarding for engineers.'\n")
    
    # Step 2: Discovery
    available_skills = agent.scan_skills()
    # Agent selects the relevant skill based on the prompt (simulated selection)
    selected_skill = available_skills[0] 
    
    # Step 3: Learning
    skill_instructions = agent.read_skill(selected_skill)
    
    # Step 4: Execution
    agent.generate_and_execute_script(skill_instructions)
```

### Explanation of What Just Happened

1.  **The Directory Scan:**
    The agent looked into `skills/`. It didn't load every tool immediately. It found `SKILL.md` inside `new_hire_onboarding`.
2.  **The "Context Load":**
    The agent read `SKILL.md`. This file is small (maybe 200 tokens).
    *   *Why this matters:* If the agent had to read the full API documentation for Bamboo, Jira, and Slack, it might have been 20,000 tokens. By reading the **Skill**, it only loaded the necessary context.
3.  **The Code Generation:**
    The agent (simulated) generated a Python script.
4.  **The Execution:**
    The script ran.
    *   It fetched 3 people (`Alice`, `Bob`, `Charlie`).
    *   It filtered out `Bob` (Sales) inside the Python environment. **The AI model never saw Bob.**
    *   It executed the Jira and Slack commands only for `Alice` and `Charlie`.

### Why `SKILL.md` is powerful
If next week you want to change the process (e.g., "Also email the manager"), you **don't change the AI**. You don't retrain the model.

You simply update `SKILL.md` to say:
> "Step 3c: Send an email to the engineering manager."

The next time the Agent reads the Skill file, it will generate the new Python script automatically. This makes your AI agents programmable via plain English documentation.