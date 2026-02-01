# Prompts module
from pathlib import Path

# Load System Prompt
_current_dir = Path(__file__).parent
SYSTEM_PROMPT = (_current_dir / "SOUL.md").read_text(encoding="utf-8")

FIBONACCI_PROMPT = "What is the 10th number in the Fibonacci sequence?"
