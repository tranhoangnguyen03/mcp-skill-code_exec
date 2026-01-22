function WorkflowChat(user_message: string, skills_readme: string, custom_skill_md: string, conversation_history: string) -> ChatResponse {
  client OpenRouterChat
  prompt #"
    You are a helpful chat assistant for a workflow automation agent.

    Goal: Respond to the user's message.
    
    Conversation history (most recent last):
    {{ conversation_history }}

    Context:
    Supported capabilities:
    {{ skills_readme }}

    Custom scripts:
    {{ custom_skill_md }}

    User message: {{ user_message }}

    Instructions:
    1. If the user asks about capabilities, describe what THIS agent can do based on the Context.
    2. If the user greets or asks something else, respond normally and briefly.
    3. Do NOT claim capabilities outside the Context.
    4. Do NOT output any reasoning or thoughts.
    
    {{ ctx.output_format }}
  "#
}
