from typing import Literal

from pydantic import BaseModel, Field


class StreamRequest(BaseModel):
    prompt: str = Field(min_length=1)
    session_id: str | None = None


class FilesystemAgentRequest(StreamRequest):
    cwd: str | None = None


class HealthResponse(BaseModel):
    status: Literal["healthy"] = "healthy"
    runtime_root: str
    prompt_source: str
    alfred_cli_available: bool
    alfred_cli_path: str | None = None

