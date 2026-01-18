client<llm> OpenRouterChat {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model env.open_router_model_name
    api_key env.open_router_api_key
  }
}
