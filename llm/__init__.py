import os
import importlib.resources

import yaml

from smolagents import CodeAgent, OpenAIServerModel

from prompts import SYSTEM_PROMPT


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

        # Load default prompt templates and override the system prompt with our project prompt
        prompt_templates = yaml.safe_load(
            importlib.resources.files("smolagents.prompts").joinpath("code_agent.yaml").read_text()
        )
        prompt_templates["system_prompt"] = SYSTEM_PROMPT

        # Initialize the model via OpenAIServerModel for OpenRouter compatibility
        self.model = OpenAIServerModel(
            model_id=self.model_id,
            api_base=self.base_url,
            api_key=self.api_key,
        )

        # Initialize the agent using custom prompt templates that include our system prompt
        self.agent = CodeAgent(
            tools=[],
            model=self.model,
            prompt_templates=prompt_templates,
        )

        print(f"LLM engine ready (OpenRouter model={self.model_id}).")

    def run(self, prompt: str) -> str:
        # Agent.run returns the result of the execution
        result = self.agent.run(prompt)
        return str(result)
