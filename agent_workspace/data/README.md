This directory stores mock seed data for the local `mcp_tools` integrations.

- Seed data lives here (JSON fixtures) so tool modules focus on behavior.
- Tools may still maintain in-memory state during a single run (e.g., created tickets/messages/events).
- Tests should remain deterministic by relying on fixtures + in-memory state resets per process.

