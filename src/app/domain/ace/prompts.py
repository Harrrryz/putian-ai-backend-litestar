"""Prompt template scaffolding for ACE roles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptTemplate:
    """Simple prompt template meta-data."""

    name: str
    version: str
    content: str


GENERATOR_PROMPT_V1 = PromptTemplate(
    name="generator-default",
    version="v1",
    content="You are the ACE Generator. Use the playbook strategies to answer.",
)

REFLECTOR_PROMPT_V1 = PromptTemplate(
    name="reflector-default",
    version="v1",
    content="You are the ACE Reflector. Analyze the generator trace.",
)

CURATOR_PROMPT_V1 = PromptTemplate(
    name="curator-default",
    version="v1",
    content="You are the ACE Curator. Convert reflections into deltas.",
)

__all__ = (
    "CURATOR_PROMPT_V1",
    "GENERATOR_PROMPT_V1",
    "PromptTemplate",
    "REFLECTOR_PROMPT_V1",
)
