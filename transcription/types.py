from typing import Any
from pydantic import BaseModel


class TranscriptWord(BaseModel):
    word: str
    start: float
    end: float
    probability: float


class TranscriptSegment(BaseModel):
    id: int
    seek: int
    start: float
    end: float
    text: str
    tokens: list[int]
    temperature: float
    avg_logprob: float
    compression_ratio: float
    no_speech_prob: float
    words: list[TranscriptWord] | None = None


class TranscriptResult(BaseModel):
    text: str
    language: str
    language_probability: float
    duration: float | None = None
    segments: list[TranscriptSegment] | None = None
    words: list[TranscriptWord] | None = None
    backend: str
    model: str
    device: str
    warnings: list[str] = []


class TranscriptionHealth(BaseModel):
    available: bool
    backend: str | None = None
    model: str | None = None
    device: str | None = None
    cuda_available: bool = False
    faster_whisper_installed: bool = False
    nemo_installed: bool = False
    warnings: list[str] = []


class TranscriptionRequest(BaseModel):
    language: str | None = None
    word_timestamps: bool = False
    backend: str | None = None
    model: str | None = None
