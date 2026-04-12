import os
import tempfile
from pathlib import Path
from typing import Any

from transcription.backends.faster_whisper_backend import get_faster_whisper_backend
from transcription.config import TranscriptionConfig
from transcription.types import TranscriptionHealth, TranscriptResult


class TranscriptionService:
    def __init__(self, config: TranscriptionConfig | None = None):
        self.config = config or TranscriptionConfig()
        self._backend = None

    @property
    def backend(self) -> Any:
        if self._backend is None:
            self._backend = self._init_backend()
        return self._backend

    def _init_backend(self) -> Any:
        backend_name = self.config.backend
        if backend_name == "faster-whisper":
            return get_faster_whisper_backend(self.config)
        elif backend_name == "parakeet":
            from transcription.backends.parakeet_backend import get_parakeet_backend

            return get_parakeet_backend(self.config)
        else:
            return get_faster_whisper_backend(self.config)

    def transcribe_file(
        self,
        audio_data: bytes,
        filename: str,
        language: str | None = None,
        word_timestamps: bool = False,
    ) -> TranscriptResult:
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp:
            tmp.write(audio_data)
            tmp_path = Path(tmp.name)

        try:
            return self.backend.transcribe(
                tmp_path,
                language=language,
                word_timestamps=word_timestamps,
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def health(self) -> TranscriptionHealth:
        cuda_available = False
        try:
            import torch

            cuda_available = torch.cuda.is_available()
        except ImportError:
            pass

        backend_health = self.backend.health_check() if self._backend else {}

        faster_whisper_ok = False
        nemo_ok = False
        try:
            import faster_whisper

            faster_whisper_ok = True
        except ImportError:
            pass
        try:
            import nemo.collections.asr

            nemo_ok = True
        except ImportError:
            pass

        return TranscriptionHealth(
            available=backend_health.get("available", False),
            backend=self.config.backend,
            model=self.config.model,
            device=self.config.device,
            cuda_available=cuda_available,
            faster_whisper_installed=faster_whisper_ok,
            nemo_installed=nemo_ok,
            warnings=backend_health.get("warnings", []),
        )


_service_instance: TranscriptionService | None = None


def get_transcription_service() -> TranscriptionService:
    global _service_instance
    if _service_instance is None:
        _service_instance = TranscriptionService()
    return _service_instance
