class Plan {
  action string
  skill_group string?
  skill_name string?
  intent string
  steps string[]
  // Multi-turn support fields
  requires_lookahead bool // Set to true when the request needs external data lookup before execution
  checkpoints string[]   // Steps that produce facts for downstream use (e.g., ["lookup_employee", "discover_domain"])
}

class ChatResponse {
  final_response string
}
