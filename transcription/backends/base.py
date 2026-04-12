from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from transcription.types import TranscriptResult


class TranscriptionBackend(ABC):
    name: str = ""

    @abstractmethod
    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        word_timestamps: bool = False,
        **kwargs: Any,
    ) -> TranscriptResult:
        """Transcribe an audio file and return the result."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend can be initialized."""
        ...

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Return health status for this backend."""
        ...
