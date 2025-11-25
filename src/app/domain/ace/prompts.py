"""Prompt template scaffolding for ACE roles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PromptTemplate:
    """Simple prompt template meta-data."""

    name: str
    version: str
    content: str

    def render(self, **kwargs: str) -> str:
        return self.content.format(**kwargs)


GENERATOR_PROMPT_V1 = PromptTemplate(
    name="generator-default",
    version="v1",
    content=(
        "You are the ACE Generator. Answer the question using the provided playbook strategies.\n"
        "Question:\n{question}\n\n"
        "Context:\n{context}\n\n"
        "Playbook Strategies:\n{strategies}\n\n"
        "Respond as JSON with keys final_answer, reasoning, strategy_ids."
    ),
)

REFLECTOR_PROMPT_V1 = PromptTemplate(
    name="reflector-default",
    version="v1",
    content=(
        "You are the ACE Reflector. Determine whether the answer was successful based on the environment feedback.\n"
        "Question:\n{question}\n\n"
        "Generator Answer:\n{final_answer}\n\n"
        "Environment Feedback:\n{environment_feedback}\n\n"
        "Respond as JSON with fields outcome (success|failure|partial), insights, "
        "and strategy_feedback (list of objects with bullet_id and classification)."
    ),
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
