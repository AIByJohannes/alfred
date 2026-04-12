from typing import Literal

from pydantic import BaseModel, Field

FS_AGENT_BACKEND_AUTO = "auto"
FS_AGENT_BACKEND_ALFRED = "alfred-cli"
FS_AGENT_BACKEND_SMOL = "smolagents"

FsAgentBackend = Literal["auto", "alfred-cli", "smolagents"]


class StreamRequest(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str | None = None
    image_base64: str | None = Field(
        default=None, description="Base64-encoded image for chat mode only"
    )


class FilesystemAgentRequest(StreamRequest):
    cwd: str | None = None
    backend: FsAgentBackend = FS_AGENT_BACKEND_AUTO


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    runtime_root: str
    prompt_source: str
    alfred_cli_available: bool
    alfred_cli_path: str | None = None
    smolagents_available: bool = True
    fs_agent_backend_options: list[str] = Field(
        default_factory=lambda: [
            FS_AGENT_BACKEND_AUTO,
            FS_AGENT_BACKEND_ALFRED,
            FS_AGENT_BACKEND_SMOL,
        ]
    )
    fs_agent_default_backend: Literal["alfred-cli", "smolagents"] = FS_AGENT_BACKEND_ALFRED


class SessionMeta(BaseModel):
    id: str
    prompt: str
    mode: str
    timestamp: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    status: Literal["done", "error", "running"] | None = None
    image_ref: str | None = None


class SessionDetail(BaseModel):
    meta: SessionMeta
    events: list[dict[str, object]]
    image_base64: str | None = None
    messages: list[Message] | None = None


class SessionCreateRequest(BaseModel):
    mode: str = "chat"


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


class TranscriptResponse(BaseModel):
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


class TranscriptionHealthResponse(BaseModel):
    available: bool
    backend: str | None = None
    model: str | None = None
    device: str | None = None
    cuda_available: bool = False
    faster_whisper_installed: bool = False
    nemo_installed: bool = False
    warnings: list[str] = []
