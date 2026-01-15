import os

from openai import OpenAI


class LLMEngine:
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        self.base_url = base_url or os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.model = model or os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

        if not self.api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Set it to initialize the LLM engine. "
                "(Example: export OPENROUTER_API_KEY='...')"
            )

        extra_headers: dict[str, str] = {}
        site_url = os.getenv("OPENROUTER_SITE_URL")
        app_name = os.getenv("OPENROUTER_APP_NAME")
        if site_url:
            extra_headers["HTTP-Referer"] = site_url
        if app_name:
            extra_headers["X-Title"] = app_name

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            default_headers=extra_headers or None,
        )

        print(f"LLM engine ready (OpenRouter model={self.model}).")

    def run(self, prompt: str) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
        )

        message = completion.choices[0].message
        return message.content or ""
