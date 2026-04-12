from pathlib import Path
from typing import Any

from transcription.backends.base import TranscriptionBackend
from transcription.config import TranscriptionConfig
from transcription.types import TranscriptResult


class ParakeetBackend(TranscriptionBackend):
    name = "parakeet"

    def __init__(self, config: TranscriptionConfig | None = None):
        self.config = config or TranscriptionConfig()
        self._model = None

    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        word_timestamps: bool = False,
        **kwargs: Any,
    ) -> TranscriptResult:
        raise NotImplementedError(
            "Parakeet backend requires NVIDIA NeMo. Install with: pip install nemo-toolkit['asr']"
        )

    def is_available(self) -> bool:
        try:
            import nemo.collections.asr as nemo_asr

            return True
        except ImportError:
            return False

    def health_check(self) -> dict[str, Any]:
        return {
            "available": self.is_available(),
            "model": self.config.model,
            "device": self.config.device,
            "error": "NeMo not installed" if not self.is_available() else None,
        }


def get_parakeet_backend(config: TranscriptionConfig | None = None) -> ParakeetBackend:
    return ParakeetBackend(config)
