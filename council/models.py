from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CouncilMember(BaseModel):
    name: str
    model: str
    role: str
    temperature: float = 0.3


class OllamaSettings(BaseModel):
    base_url: str = "http://localhost:11434"
    request_timeout_seconds: int = 120


class AppSettings(BaseModel):
    runs_path: str = "runs.jsonl"


class Settings(BaseModel):
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)
    app: AppSettings = Field(default_factory=AppSettings)
    council: list[CouncilMember]


class CandidateAnswer(BaseModel):
    label: str
    member_name: str
    model: str
    answer: str


class Vote(BaseModel):
    member_name: str
    model: str
    vote: Optional[str] = None
    reason: str = ""
    raw_response: str = ""
    valid: bool = True
    error: Optional[str] = None


class CouncilRun(BaseModel):
    created_at: datetime = Field(default_factory=utc_now)
    prompt: str
    candidates: list[CandidateAnswer]
    votes: list[Vote]
    vote_counts: dict[str, int]
    winner_label: Optional[str]
    final_answer: Optional[str]
    errors: list[str] = Field(default_factory=list)
