from core.llm import LLMEngine

def main():
    """
    Main function to run the application.
    """

    from core.prompts import FIBONACCI_PROMPT
    engine = LLMEngine()
    print(f"Running agent with prompt: '{FIBONACCI_PROMPT}'")
    result = engine.run(FIBONACCI_PROMPT)

    print("\n--- Agent's Final Answer ---")
    print(result)


if __name__ == "__main__":
    main()