Read [](docs/AI_AGENT_ARCHITECTURE.md#1-1), lines 1 to 400

Read [](docs/AI_AGENT_ARCHITECTURE.md#401-401), lines 401 to 798

Read [](docs/AGENT_SESSIONS_MANAGEMENT.md#1-1), lines 1 to 400

Read [](docs/AGENT_SESSIONS_MANAGEMENT.md#401-401), lines 401 to 800

Read [](docs/AGENT_SESSIONS_MANAGEMENT.md#801-801), lines 801 to 1200

Read [](docs/AGENT_SESSIONS_MANAGEMENT.md#1201-1201), lines 1201 to 1462

Read [](docs/TOOL_DEFINITION_SYSTEM.md#1-1), lines 1 to 400

Read [](docs/TOOL_DEFINITION_SYSTEM.md#401-401), lines 401 to 800

Read [](docs/TOOL_DEFINITION_SYSTEM.md#801-801), lines 801 to 1200

Read [](docs/TOOL_DEFINITION_SYSTEM.md#1201-1201), lines 1201 to 1695

Read [](src/app/domain/todo_agents/services.py#1-1), lines 1 to 400

Read [](src/app/domain/todo_agents/services.py#401-401), lines 401 to 441

Read [](src/app/domain/todo_agents/tools/tool_context.py)

Read [](src/app/domain/todo_agents/tools/tool_definitions.py)

Read [](src/app/domain/todo_agents/tools/argument_models.py)

Read [](src/app/domain/todo_agents/tools/tool_implementations.py#1-1), lines 1 to 400

Read [](src/app/domain/todo_agents/tools/tool_implementations.py#401-401), lines 401 to 800

Read [](src/app/domain/todo_agents/tools/tool_implementations.py#801-801), lines 801 to 988

Read [](src/app/domain/todo_agents/tools/universal_tools.py)

Read [](src/app/domain/todo_agents/tools/agent_factory.py)

Read [](src/app/domain/todo_agents/tools/system_instructions.py)

Searched for files matching `**/todo_agents/**/*.py`, 15 matches

Read [](src/app/domain/todo_agents/controllers/todo_agents.py)

Read [](src/app/domain/todo_agents/schemas.py)

Read [](src/app/domain/todo_agents/deps.py)

Read [](src/app/domain/agent_sessions)

Read [](src/app/domain/agent_sessions/services.py)

**ACE Implementation Plan**
- **Foundation & Domain Scaffolding**: Introduce a dedicated `src/app/domain/ace` package mirroring existing domain layout (controllers/services/schemas) plus `roles.py`, `playbook.py`, `delta.py`, `adaptation.py`, `llm.py`, and `prompts.py` modules; wire new package into __init__.py, urls.py, and dependency providers. Extend pyproject.toml / `__all__` exports only where necessary to keep tooling aware.
- **Playbook Persistence Layer**: Add SQLAlchemy models `AcePlaybookBullet` and `AcePlaybookSection` (with helpful/harmful counters, metadata JSON, timestamps) under `src/app/db/models/ace_playbook.py`, generate Alembic migration, and surface repository & service classes (Advanced Alchemy style) to expose CRUD plus atomic delta application (`ADD/UPDATE/TAG/REMOVE`). Ensure indexing on `(section, created_at)` and uniqueness on bullet IDs, and update docs with schema notes.
- **LLM Abstraction & Prompt Engine**: Implement `ace/llm.py` with a provider-agnostic `LLMClient` interface (async `generate`, built-in retry/timeout, litellm/OpenAI adapter) and observability hooks (structlog + optional Opik trace IDs). Encode role-specific prompt templates and JSON schema contracts in `ace/prompts.py`, versioned via enumerations and load helpers, leveraging patterns from existing `todo_agents` instructions.
- **Role Implementations**: Build concrete `GeneratorRole`, `ReflectorRole`, `CuratorRole` classes in `ace/roles.py` that accept the LLM client, playbook accessor, and tool for environment feedback. Generator should accept playbook context slices and emit structured outputs (final answer, strategy IDs, reasoning chain); Reflector processes agent transcript + environment verdict + canonical answer to classify strategies; Curator converts reflections into normalized `DeltaOperation` objects (defined in `ace/delta.py`) with idempotency protection and de-duplication logic. Provide shared dataclasses / Pydantic models for role IO.
- **Adaptation Pipelines**: Author `ace/adaptation.py` with orchestrators `OfflineAdapter` and `OnlineAdapter` that coordinate `Generator → Environment → Reflector → Curator → Playbook` loops. Support pluggable environment evaluators (sync/async callouts), configurable retry windows, and instrumentation (metrics/events). Ensure offline loop handles dataset iteration with batch commits; online loop integrates gracefully with live request flow.
- **Todo Agent Integration**: Enhance `todo_agents` service layer (services.py) to optionally run requests through ACE. Add a thin `AceOrchestrator` bridge that wraps `TodoAgentService.chat_with_agent` to: 1) hydrate playbook snapshot, 2) run Generator with existing `Runner` and capture tool trace, 3) call Reflector with user/environment feedback (initially derived from success heuristics, extensible). Update `tool_context` to expose playbook bullets when generator needs citing, and adjust system_instructions.py to reference dynamic strategies (inject via template placeholders at runtime). Preserve existing behavior behind feature flags (`settings.ai.enable_ace`).
- **Delta Application & Rollback**: Within `playbook.py`, implement transactional application of curator deltas with audit logging and rollback journal (e.g., `AcePlaybookRevision` table). Provide CLI/service endpoints to inspect revisions, revert harmful updates, and flush caches. Expose helpful/harmful counters through services to support progressive pruning.
- **APIs & Session Storage**: Add optional endpoints (Litestar controller) under `/ace/playbook` for retrieving sections, submitting manual deltas, and inspecting metrics, following existing controller patterns and JWT guards. Persist role transcripts and reflections by extending `agent_sessions` (linking bullet usage to `SessionMessage.extra_data`) to maintain the “decision causal chain”.
- **Offline Training Pipelines**: Create CLI commands (e.g., `manage.py ace-offline-train`) that load historical datasets, feed them through `OfflineAdapter`, and write updated playbooks. Support resumable checkpoints and evaluation metrics (success rate deltas, helpful/harmful ratios). Document expected dataset schema in `docs/ACE_FRAMEWORK.md`.
- **Configuration & Settings**: Extend base.py and `app/config/constants.py` with ACE toggles (enable flags, default model alias, dataset paths, retry limits). Ensure `.env.sample` and docs list new env vars. Inject settings via dependency providers for easy test overrides.
- **Testing Strategy**: Add unit suites under `tests/unit/ace` covering role prompts, delta semantics, and playbook persistence; write integration tests exercising end-to-end online loop against a stub LLM/environment (use pytest fixtures as in data_fixtures.py). Update existing agent tests to verify ACE-disabled baseline remains unchanged and ACE-enabled path tags strategies correctly. Include regression tests for migration schema.
- **Observability & Metrics**: Instrument roles and adapters with structlog context (session_id, strategy_ids, outcome) and expose counters (e.g., Prometheus-style via existing monitoring hooks). Add hooks for rate limiting interplay to avoid double-counting when ACE replays generator runs.
- **Documentation & Developer Workflow**: Produce new docs (`docs/ACE_FRAMEWORK.md`, update `WIKI_TOC.md`, cross-link from AI agent guides) detailing architecture, configuration, and operational playbook management. Provide quickstart instructions and troubleshooting. Finally, update Makefile targets where needed (lint/test coverage) and ensure pre-commit passes with new modules.

Suggested next moves: 1) scaffold `ace` domain package + DB models/migration, 2) implement playbook services/deltas with tests, 3) hook generator integration behind feature flag and iterate end-to-end.