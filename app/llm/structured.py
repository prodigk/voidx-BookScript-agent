"""Responses API structured-output wrapper with bounded retries."""

from __future__ import annotations

import logging
import time
from typing import Protocol, TypeVar

from openai import OpenAI
from pydantic import BaseModel

from app.config import LLMSettings

LOGGER = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class StructuredProvider(Protocol):
    def parse(self, *, stage: str, instructions: str, input_text: str, output_type: type[T]) -> T: ...


class OpenAIStructuredProvider:
    def __init__(self, settings: LLMSettings) -> None:
        self.settings = settings
        self.client = OpenAI()

    def parse(self, *, stage: str, instructions: str, input_text: str, output_type: type[T]) -> T:
        for attempt in range(self.settings.max_retries + 1):
            try:
                response = self.client.responses.parse(
                    model=self.settings.model,
                    instructions=instructions,
                    input=input_text,
                    text_format=output_type,
                    max_output_tokens=self.settings.max_output_tokens,
                    store=False,
                    text={"verbosity": "low"},
                )
                parsed = response.output_parsed
                if parsed is None:
                    raise ValueError("Structured response did not contain parsed output")
                usage = response.usage
                LOGGER.info(
                    "LLM call complete: stage=%s model=%s input_tokens=%s output_tokens=%s attempt=%d",
                    stage, self.settings.model, getattr(usage, "input_tokens", None),
                    getattr(usage, "output_tokens", None), attempt + 1,
                )
                return parsed
            except Exception as exc:
                if attempt >= self.settings.max_retries:
                    LOGGER.error(
                        "LLM stage failed: stage=%s model=%s error_type=%s",
                        stage, self.settings.model, type(exc).__name__,
                    )
                    raise RuntimeError(f"Structured LLM stage failed: {stage} ({type(exc).__name__})") from None
                delay = min(2**attempt, 4)
                LOGGER.warning("Retrying malformed/failed structured output: stage=%s delay=%ds", stage, delay)
                time.sleep(delay)
        raise RuntimeError("Unreachable structured output retry state")
