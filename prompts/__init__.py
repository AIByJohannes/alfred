from pathlib import Path

_current_dir = Path(__file__).parent
SYSTEM_PROMPT = (_current_dir / "SOUL.md").read_text(encoding="utf-8")
