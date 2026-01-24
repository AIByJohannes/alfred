import os

from smolagents import CodeAgent, OpenAIServerModel


class LLMEngine:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model_id = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Set it to initialize the LLM engine. "
                "(Example: export OPENROUTER_API_KEY='...')"
            )

        # Initialize the model via OpenAIServerModel for OpenRouter compatibility
        self.model = OpenAIServerModel(
            model_id=self.model_id,
            api_base=self.base_url,
            api_key=self.api_key,
        )

        # Initialize the agent
        # We use CodeAgent as the default agent type for flexibility
        self.agent = CodeAgent(tools=[], model=self.model)

        print(f"LLM engine ready (OpenRouter model={self.model_id}).")

    def run(self, prompt: str) -> str:
        # Agent.run returns the result of the execution
        result = self.agent.run(prompt)
        return str(result)
