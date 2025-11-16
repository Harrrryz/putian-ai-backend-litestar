# ACE Framework Implementation Plan

## 1. Foundation & Domain Scaffolding
- Introduce `src/app/domain/ace` package mirroring existing domain layout (controllers, services, schemas) plus dedicated modules: `roles.py`, `playbook.py`, `delta.py`, `adaptation.py`, `llm.py`, and `prompts.py`.
- Register the new package in `app/domain/__init__.py`, add URL + dependency plumbing, and extend exports only where required.
- Update project docs and tooling references to recognize the ACE domain.

## 2. Playbook Persistence Layer
- Add SQLAlchemy models `AcePlaybookBullet` and `AcePlaybookSection` with helpful/harmful counters, metadata JSON, and timestamps under `src/app/db/models/ace_playbook.py`.
- Generate an Alembic migration to create tables, enforce bullet ID uniqueness, and index `(section, created_at)`.
- Implement repository and service classes (Advanced Alchemy pattern) enabling CRUD plus atomic delta application (`ADD`, `UPDATE`, `TAG`, `REMOVE`).
- Document schema expectations in `docs/` (reference from the new plan doc and wiki).

## 3. LLM Abstraction & Prompt Engine
- Build `ace/llm.py` defining an async `LLMClient` interface with retry, timeout, and observability hooks (structlog + optional Opik integration).
- Provide adapters for LiteLLM/OpenAI and configuration-driven model selection.
- Encode role-specific prompt templates and JSON schemas in `ace/prompts.py`, versioned for evolution and leveraging existing instruction patterns.

## 4. Role Implementations
- Implement `GeneratorRole`, `ReflectorRole`, and `CuratorRole` in `ace/roles.py`, each using the shared `LLMClient` and playbook access APIs.
- Define structured IO models (Pydantic) ensuring generator outputs include reasoning traces, final answer, and referenced strategy IDs.
- Have Reflector classify strategy usage as helpful/harmful/neutral based on environment feedback and canonical answers.
- Curator converts reflections into normalized delta operations with idempotency checks and deduplication.

## 5. Adaptation Pipelines
- Author `ace/adaptation.py` orchestrating `Generator → Environment → Reflector → Curator → Playbook` loops.
- Implement `OfflineAdapter` for dataset-driven training epochs with batched playbook commits.
- Implement `OnlineAdapter` for real-time updates with configurable retry limits and metrics emission.
- Support pluggable environment evaluators (sync/async) to score generator outputs against ground truth.

## 6. Todo Agent Integration
- Extend `TodoAgentService` to optionally route interactions through ACE when enabled via settings.
- Add an `AceOrchestrator` bridge wrapping `chat_with_agent` to hydrate playbook snapshots, run the generator, capture tool traces, and trigger reflection/curation.
- Expose playbook strategies to prompt construction by updating `tool_context` and injecting dynamic strategy summaries into `system_instructions`.
- Guard new behavior behind a feature flag (`settings.ai.enable_ace`) to preserve current behavior by default.

## 7. Delta Application & Rollback
- Implement transactional delta application in `playbook.py`, writing audit entries (`AcePlaybookRevision`) for rollback support.
- Provide CLI/service helpers to inspect revisions, revert harmful updates, and rebuild cached playbook materializations.
- Ensure counter updates (helpful/harmful) remain consistent under concurrent writes.

## 8. APIs & Session Storage
- Add Litestar controllers under `/ace/playbook` for retrieving sections, submitting manual deltas, and reviewing metrics with existing JWT guards.
- Extend `agent_sessions` to persist role transcripts and link bullet IDs via `SessionMessage.extra_data`, creating the decision causal chain.
- Surface helpful/harmful tallies in API responses for analytics dashboards.

## 9. Offline Training Pipelines
- Create CLI commands (for example `manage.py ace-offline-train`) that replay historical datasets through `OfflineAdapter` and emit updated playbooks.
- Support resumable checkpoints, validation splits, and summary metrics (success rate deltas, helpful/harmful ratios).
- Document dataset schema expectations and operational workflow in supporting docs.

## 10. Configuration & Settings
- Extend `src/app/config/base.py` (and related constants) with ACE toggles, model choices, retry limits, and dataset paths.
- Update `.env.sample` and README/doc references to include the new environment variables.
- Provide dependency providers so tests and services can override ACE settings easily.

## 11. Testing Strategy
- Add unit suites under `tests/unit/ace` covering delta semantics, playbook persistence, and prompt assembly.
- Write integration tests that exercise an end-to-end ACE loop with stubbed LLM/environment components.
- Ensure existing agent tests verify both ACE-disabled and ACE-enabled paths without regressions (including tool usage citations).
- Include migration tests verifying schema creation and rollback paths.

## 12. Observability & Metrics
- Instrument roles and adapters with structlog context (session ID, strategy IDs, outcome) and expose counters for Prometheus/exporter pipelines.
- Hook into existing rate limit metrics to avoid double-counting when ACE replays generator runs.
- Provide dashboards or log aggregation queries documenting key ACE KPIs (success rate, delta volume, harmful strategy count).

## 13. Documentation & Developer Workflow
- Author `docs/ACE_FRAMEWORK.md` (or similar) detailing architecture, configuration, operational procedures, and troubleshooting.
- Update `docs/WIKI_TOC.md` and related AI agent guides to link the new documentation.
- Refresh Makefile/CI targets if new lint/test coverage paths are required and ensure pre-commit hooks cover ACE modules.
- Share quickstart guidance for enabling ACE locally and for running offline adaptation jobs.

## Suggested Next Steps
1. Scaffold the ACE domain package, database models, and corresponding migration.
2. Implement playbook services plus delta logic with focused tests.
3. Integrate ACE into the todo agent behind the feature flag and validate the end-to-end loop.
