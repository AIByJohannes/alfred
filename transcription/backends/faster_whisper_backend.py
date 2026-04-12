import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

FASTER_WHISPER_AVAILABLE = False
WhisperModel = None

try:
    from faster_whisper import WhisperModel as _WhisperModel

    FASTER_WHISPER_AVAILABLE = True
    WhisperModel = _WhisperModel
except ImportError:
    pass

from transcription.backends.base import TranscriptionBackend
from transcription.config import TranscriptionConfig
from transcription.types import (
    TranscriptResult,
    TranscriptSegment,
    TranscriptWord,
)


class FasterWhisperBackend(TranscriptionBackend):
    name = "faster-whisper"

    def __init__(self, config: TranscriptionConfig | None = None):
        self.config = config or TranscriptionConfig()
        self._model: Any = None

    @property
    def model(self) -> Any:
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )
        if self._model is None:
            self._model = self._load_model()
        return self._model

    def _load_model(self) -> Any:
        model_size = self._resolve_model_size(self.config.model)
        return WhisperModel(
            model_size,
            device=self.config.device,
            compute_type=self.config.compute_type,
            download_root=self.config.cache_dir,
        )

    def _resolve_model_size(self, model_id: str) -> str:
        """Map model IDs to faster-whisper model sizes."""
        model_map = {
            "openai/whisper-large-v3-turbo": "large-v3",
            "openai/whisper-large-v3": "large-v3",
            "openai/whisper-large-v2": "large-v2",
            "openai/whisper-medium": "medium",
            "openai/whisper-small": "small",
            "openai/whisper-base": "base",
            "openai/whisper-tiny": "tiny",
            "distil-whisper/distil-large-v3": "distil-large-v3",
            "distil-whisper/distil-medium.en": "distil-medium.en",
            "Systran/faster-distil-whisper-large-v3": "distil-large-v3",
        }
        for key, value in model_map.items():
            if model_id.lower().endswith(key.lower()) or key in model_id:
                return value
        return "large-v3"

    def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
        word_timestamps: bool = False,
        **kwargs: Any,
    ) -> TranscriptResult:
        if not FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper not installed. Install with: pip install faster-whisper"
            )

        language = language or self.config.language
        word_timestamps = word_timestamps or self.config.word_timestamps

        vad_filter = self.config.vad if "vad_filter" not in kwargs else kwargs["vad_filter"]

        segments, info = self.model.transcribe(
            str(audio_path),
            language=language if language != "auto" else None,
            word_timestamps=word_timestamps,
            vad_filter=vad_filter,
            chunk_length_s=self.config.chunk_seconds,
            batch_size=self.config.batch_size,
        )

        segments_list = []
        all_words = []
        full_text_parts = []

        for idx, segment in enumerate(segments):
            seg_dict = segment._asdict() if hasattr(segment, "_asdict") else {}
            seg_words = None
            if word_timestamps and hasattr(segment, "words") and segment.words:
                seg_words = [
                    TranscriptWord(
                        word=w.word,
                        start=w.start,
                        end=w.end,
                        probability=w.probability,
                    )
                    for w in segment.words
                ]
                all_words.extend(seg_words)

            segments_list.append(
                TranscriptSegment(
                    id=idx,
                    seek=int(seg_dict.get("seek", 0)),
                    start=segment.start,
                    end=segment.end,
                    text=segment.text,
                    tokens=seg_dict.get("tokens", []),
                    temperature=seg_dict.get("temperature", 0.0),
                    avg_logprob=seg_dict.get("avg_logprob", 0.0),
                    compression_ratio=seg_dict.get("compression_ratio", 0.0),
                    no_speech_prob=seg_dict.get("no_speech_prob", 0.0),
                    words=seg_words,
                )
            )
            full_text_parts.append(segment.text)

        result_text = " ".join(full_text_parts).strip()
        warnings = []
        if info.language_probability < 0.5:
            warnings.append(f"Low language detection confidence: {info.language_probability:.2f}")

        return TranscriptResult(
            text=result_text,
            language=info.language or "unknown",
            language_probability=info.language_probability,
            duration=info.duration,
            segments=segments_list if segments_list else None,
            words=all_words if all_words else None,
            backend=self.name,
            model=self.config.model,
            device=self.config.device,
            warnings=warnings,
        )

    def is_available(self) -> bool:
        return FASTER_WHISPER_AVAILABLE

    def health_check(self) -> dict[str, Any]:
        import torch

        return {
            "available": self.is_available(),
            "model": self.config.model,
            "device": self.config.device,
            "compute_type": self.config.compute_type,
            "cuda_available": torch.cuda.is_available(),
        }


def get_faster_whisper_backend(config: TranscriptionConfig | None = None) -> FasterWhisperBackend:
    return FasterWhisperBackend(config)
