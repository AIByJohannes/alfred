from typing import Literal

BackendType = Literal["faster-whisper", "parakeet"]

ComputeType = Literal["float32", "float16", "int8", "int8_float16"]

DeviceType = Literal["cuda", "cpu"]


class TranscriptionConfig:
    def __init__(
        self,
        backend: BackendType | None = None,
        model: str | None = None,
        device: DeviceType | None = None,
        compute_type: ComputeType | None = None,
        language: str | None = None,
        word_timestamps: bool = False,
        vad: bool = True,
        chunk_seconds: int = 30,
        batch_size: int = 8,
        cache_dir: str | None = None,
    ):
        self.backend = backend or "faster-whisper"
        self.model = model or "openai/whisper-large-v3-turbo"
        self.device = device or ("cuda" if _has_cuda() else "cpu")
        self.compute_type = compute_type or ("float16" if self.device == "cuda" else "int8")
        self.language = language or "auto"
        self.word_timestamps = word_timestamps
        self.vad = vad
        self.chunk_seconds = chunk_seconds
        self.batch_size = batch_size
        self.cache_dir = cache_dir or ".alfred-runtime/models/transcription"


def _has_cuda() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except ImportError:
        return False
