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


class SessionDetail(BaseModel):
    meta: SessionMeta
    events: list[dict[str, object]]
    image_base64: str | None = None


class SessionCreateRequest(BaseModel):
    mode: str = "chat"
