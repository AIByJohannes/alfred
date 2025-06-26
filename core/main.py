from smolagents import CodeAgent, LiteLLMModel, PythonInterpreterTool

def main():
    """
    Main function to run the application.
    """
    try:
        model = LiteLLMModel(model_id="ollama_chat/qwen2:7b")
        print("Successfully connected to the Ollama model.")
    except Exception as e:
        print(f"Failed to connect to the model. Make sure Ollama is running and the model is available. Error: {e}")
        exit()

    agent = CodeAgent(model=model, tools=[PythonInterpreterTool()])
    print("Agent created successfully.")

    prompt = "What is the 10th number in the Fibonacci sequence?"
    print(f"Running agent with prompt: '{prompt}'")

    result = agent.run(prompt)

    print("\n--- Agent's Final Answer ---")
    print(result)


if __name__ == "__main__":
    main()