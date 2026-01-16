# Skill: Performance Review Cycle

## Description
Initiates the quarterly performance review process for eligible employees.

## Dependencies
- mcp_tools.lattice
- mcp_tools.slack
- mcp_tools.bamboo_hr

## Inputs
- Cycle Name: `cycle_name` (string). E.g., "Q3 2023 Review".
- Due Date: `due_date` (YYYY-MM-DD).
- Minimum Tenure (days): `min_tenure` (int). Default: 90.

## Action Steps
1. Create a review cycle in the performance platform (Lattice).
2. Identify employees eligible for review based on tenure.
3. Notify eligible employees via Slack to begin their self-assessments.
4. Notify managers to prepare for reviews.

## Logic Flow
1. **Create Cycle**:
   - Call `lattice.create_cycle(name=cycle_name, due_date=due_date)`.

2. **Identify Eligible Employees**:
   - Call `lattice.get_eligible_employees(min_tenure_days=min_tenure)`.
   - Store list as `eligible_users`.

3. **Notify Employees**:
   - For each user in `eligible_users`:
     - Look up their Slack ID (mock logic or assume stored in user object).
     - Call `slack.send_dm(user_id=user["id"], message=f"Performance reviews have started! Please complete your self-assessment by {due_date}.")`.

4. **Summary**:
   - Print f"Launched cycle '{cycle_name}'. Notified {len(eligible_users)} employees."

## Notes
- This workflow triggers the *start* of the cycle.
- In a real scenario, you might cross-reference `bamboo_hr` to get Slack IDs if `lattice` doesn't have them. For this mock, we assume `lattice` user IDs can map to Slack or we print the intended action.
