"""Application configuration loaded from YAML with environment overrides."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic.types import SecretStr


class ProjectSettings(BaseModel):
    language: str = "ko"
    library_path: Path = Path("library")
    output_path: Path = Path("outputs")
    database_path: Path = Path("data/database.sqlite")
    metadata_path: Path = Path("metadata/books.yaml")
    audit_report_path: Path = Path("reports/library_audit.md")


class LoggingSettings(BaseModel):
    level: str = "INFO"


class IngestionSettings(BaseModel):
    ignored_directories: set[str] = Field(
        default_factory=lambda: {"outputs", "reports", "data", "metadata", ".git", ".venv"}
    )


class ChunkingSettings(BaseModel):
    min_chars: int = Field(default=200, ge=1)
    target_chars: int = Field(default=800, ge=1)
    max_chars: int = Field(default=1500, ge=1)
    overlap_chars: int = Field(default=150, ge=0)

    def model_post_init(self, __context: Any) -> None:
        if not self.min_chars <= self.target_chars <= self.max_chars:
            raise ValueError("Chunk sizes must satisfy min_chars <= target_chars <= max_chars")
        if self.overlap_chars >= self.max_chars:
            raise ValueError("overlap_chars must be smaller than max_chars")


class IndexingSettings(BaseModel):
    watch_interval_seconds: float = Field(default=10.0, gt=0)


class EmbeddingSettings(BaseModel):
    model: str = "text-embedding-3-small"
    dimensions: int = Field(default=1536, ge=1)
    batch_size: int = Field(default=100, ge=1, le=2048)
    max_retries: int = Field(default=3, ge=0, le=10)


class LLMSettings(BaseModel):
    model: str = "gpt-5-mini"
    max_retries: int = Field(default=2, ge=0, le=5)
    max_output_tokens: int = Field(default=4000, ge=256)


class ScriptSettings(BaseModel):
    characters_per_minute: int = Field(default=320, ge=100, le=1000)
    length_tolerance: float = Field(default=0.35, ge=0.1, le=0.75)
    max_output_tokens: int = Field(default=10000, ge=1000)


class VideoSettings(BaseModel):
    primary_renderer: str = Field(default="remotion", min_length=1)
    fps: int = Field(default=30, ge=1, le=120)
    width: int = Field(default=1920, ge=640, le=7680)
    height: int = Field(default=1080, ge=360, le=4320)
    project_path: Path = Path("video")
    audio_filename: str = Field(default="narration.mp3", min_length=1)


class InsightSettings(BaseModel):
    enabled: bool = True
    path: Path = Path("insights")
    manifest_path: Path = Path("data/insights/manifest.json")
    default_profile: str = "잠들기전 교양이"
    max_context_chars: int = Field(default=18000, ge=2000, le=100000)
    max_documents: int = Field(default=5, ge=1, le=50)


class BackendSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
    )
    max_concurrent_jobs: int = Field(default=1, ge=1, le=4)
    api_token: SecretStr | None = None


class RetrievalWeights(BaseModel):
    keyword: float = Field(default=0.30, ge=0)
    semantic: float = Field(default=0.45, ge=0)
    metadata: float = Field(default=0.15, ge=0)
    diversity: float = Field(default=0.10, ge=0)


class RetrievalDiversity(BaseModel):
    enabled: bool = True
    same_book_penalty: float = Field(default=0.15, ge=0)


class RetrievalLimits(BaseModel):
    candidate_pool: int = Field(default=100, ge=10, le=1000)
    max_chunks_per_book: int = Field(default=5, ge=1)


class RetrievalSettings(BaseModel):
    weights: RetrievalWeights = Field(default_factory=RetrievalWeights)
    diversity: RetrievalDiversity = Field(default_factory=RetrievalDiversity)
    limits: RetrievalLimits = Field(default_factory=RetrievalLimits)


class BookSelectionSettings(BaseModel):
    screening_count: int = Field(default=20, ge=10, le=30)
    candidate_count: int = Field(default=10, ge=2, le=30)
    default_selected_count: int = Field(default=3, ge=2, le=4)
    min_selected_count: int = Field(default=2, ge=1, le=4)
    max_selected_count: int = Field(default=4, ge=2, le=6)


class Settings(BaseModel):
    project: ProjectSettings = Field(default_factory=ProjectSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    chunking: ChunkingSettings = Field(default_factory=ChunkingSettings)
    indexing: IndexingSettings = Field(default_factory=IndexingSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    script: ScriptSettings = Field(default_factory=ScriptSettings)
    video: VideoSettings = Field(default_factory=VideoSettings)
    insights: InsightSettings = Field(default_factory=InsightSettings)
    backend: BackendSettings = Field(default_factory=BackendSettings)
    book_selection: BookSelectionSettings = Field(default_factory=BookSelectionSettings)


def load_settings(config_path: Path | None = None) -> Settings:
    """Load settings from YAML and apply supported environment overrides."""
    load_dotenv()
    path = config_path or Path(os.getenv("CONFIG_PATH", "config/default.yaml"))
    raw: dict[str, Any] = {}
    if path.exists():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Configuration root must be a mapping: {path}")
        raw = loaded

    project = raw.setdefault("project", {})
    logging_config = raw.setdefault("logging", {})
    indexing_config = raw.setdefault("indexing", {})
    embedding_config = raw.setdefault("embedding", {})
    llm_config = raw.setdefault("llm", {})
    script_config = raw.setdefault("script", {})
    video_config = raw.setdefault("video", {})
    insight_config = raw.setdefault("insights", {})
    backend_config = raw.setdefault("backend", {})
    overrides = {
        "LIBRARY_PATH": (project, "library_path"),
        "OUTPUT_PATH": (project, "output_path"),
        "DATABASE_PATH": (project, "database_path"),
        "METADATA_PATH": (project, "metadata_path"),
        "AUDIT_REPORT_PATH": (project, "audit_report_path"),
        "LOG_LEVEL": (logging_config, "level"),
        "INDEX_WATCH_INTERVAL": (indexing_config, "watch_interval_seconds"),
        "EMBEDDING_MODEL": (embedding_config, "model"),
        "EMBEDDING_DIMENSIONS": (embedding_config, "dimensions"),
        "OPENAI_MODEL": (llm_config, "model"),
        "SCRIPT_MAX_OUTPUT_TOKENS": (script_config, "max_output_tokens"),
        "VIDEO_RENDERER": (video_config, "primary_renderer"),
        "VIDEO_WIDTH": (video_config, "width"),
        "VIDEO_HEIGHT": (video_config, "height"),
        "VIDEO_PROJECT_PATH": (video_config, "project_path"),
        "VIDEO_AUDIO_FILENAME": (video_config, "audio_filename"),
        "INSIGHTS_PATH": (insight_config, "path"),
        "INSIGHT_PROFILE": (insight_config, "default_profile"),
        "BACKEND_HOST": (backend_config, "host"),
        "BACKEND_PORT": (backend_config, "port"),
        "BACKEND_MAX_CONCURRENT_JOBS": (backend_config, "max_concurrent_jobs"),
        "LOCAL_API_TOKEN": (backend_config, "api_token"),
    }
    for env_name, (section, key) in overrides.items():
        if value := os.getenv(env_name):
            section[key] = value
    if origins := os.getenv("ALLOWED_ORIGINS"):
        backend_config["allowed_origins"] = [item.strip() for item in origins.split(",") if item.strip()]
    return Settings.model_validate(raw)


def load_retrieval_settings(path: Path = Path("config/retrieval.yaml")) -> RetrievalSettings:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    return RetrievalSettings.model_validate(raw or {})
