# Abstraction over smolagents for LLM agent usage

from smolagents import CodeAgent, LiteLLMModel, PythonInterpreterTool

class LLMEngine:
    def __init__(self, model_id="ollama_chat/qwen2:7b"):
        try:
            self.model = LiteLLMModel(model_id=model_id)
            print("Successfully connected to the Ollama model.")
        except Exception as e:
            print(f"Failed to connect to the model. Make sure Ollama is running and the model is available. Error: {e}")
            raise
        self.agent = CodeAgent(model=self.model, tools=[PythonInterpreterTool()])
        print("Agent created successfully.")

    def run(self, prompt: str):
        return self.agent.run(prompt)
