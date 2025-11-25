# ACE Framework Guide

This document explains how the ACE (Agentic Context Engineering) framework works inside the todo backend, how to enable it, and how to extend or operate it safely.

## What ACE Does
- Adds a playbook of strategies (bullets grouped into sections) that the agent can cite and learn from.
- Wraps the agent loop with Generator → Reflector → Curator roles that apply structured feedback to the playbook.
- Supports offline training and online adaptation with auditability and rollback through revisions.

## Architecture Overview
- **Domain package**: `src/app/domain/ace`
  - `playbook.py`: High-level playbook service with snapshot loading and delta application (ADD/UPDATE/TAG/REMOVE) plus revision logging.
  - `delta.py`: Delta operation model and validation.
  - `services.py`: Repository services for sections, bullets, and revisions.
  - `orchestrator.py`: Runtime bridge that injects strategies into agent instructions and records helpful/harmful tags.
  - `roles.py`: Generator/Reflector/Curator role implementations with structured I/O.
  - `adaptation.py`: Offline/online adapters that wire roles with environment evaluation and delta commits.
  - `prompts.py`: Versioned prompt templates with JSON output contracts.
  - `controllers/`: Playbook HTTP controller exposing sections, revisions, and delta submission.
  - `deps.py`: DI providers for playbook services.
- **Persistence**:
  - Models: `AcePlaybookSection`, `AcePlaybookBullet`, `AcePlaybookRevision` under `src/app/db/models/ace_playbook.py`.
  - Migration: `src/app/db/migrations/versions/2025-11-17_add_ace_playbook_tables_98ba423688c9.py`.
- **Todo agent integration**:
  - `TodoAgentService` feature-flagged ACE injection and feedback tagging.
  - `AceOrchestrator` merges top strategies into system instructions and records TAG deltas after runs.
  - System instructions can be overridden per-run via `get_todo_agent(instructions=...)`.

## Data Model
- **Section**: `name`, `display_name`, optional `description`, `ordering`, `metadata`.
- **Bullet**: `bullet_id` (unique), `content`, `section_id`, counters `helpful_count`/`harmful_count`, `metadata`.
- **Revision**: `operations` (applied deltas), `applied_by`, `description`, `metadata`, timestamps.
- Indices: `ace_playbook_bullet(section_id, created_at)`, unique bullet IDs, unique section names.

## APIs
- Base path: `/ace/playbook`
  - `GET /sections`: Returns ordered sections with bullets.
  - `GET /revisions?limit=N`: Returns recent revision entries.
  - `POST /delta`: Apply deltas (ADD/UPDATE/TAG/REMOVE). Body: `{ operations: [DeltaOperation], description?, applied_by?, metadata? }`.
- See `src/app/domain/ace/controllers/playbook.py` for payload shapes and response models.

## Configuration & Flags
- `.env*`:
  - `AI_ENABLE_ACE` (bool): enable ACE integration in `TodoAgentService`.
  - `AI_ACE_MODEL` (str): model alias for ACE prompts (default `openai/gpt-4o-mini`).
  - `AI_ACE_MAX_STRATEGIES` (int): max strategies to inject into prompts per run.
- Settings live in `src/app/config/base.py` (`AISettings`).

## Runtime Flow (ACE-enabled)
1. `TodoAgentService.chat_with_agent/stream_chat_with_agent` builds system instructions.
2. If ACE is enabled, `AceOrchestrator.build_context_block()` loads top strategies (ordered by helpful-harmful score and recency) and appends them to instructions, capturing bullet IDs.
3. Agent runs; final message is inspected for `[ACE:<strategy_id>]` tags (or falls back to injected IDs).
4. `record_feedback` applies TAG deltas (helpful or harmful) and writes a revision.

## Roles & Adapters (extensible)
- **GeneratorRole**: LLM call producing `final_answer`, `reasoning`, and `strategy_ids`. Prompt enforces JSON output.
- **ReflectorRole**: LLM call classifying outcome and generating `strategy_feedback` (helpful/harmful/neutral).
- **CuratorRole**: Converts feedback into `DeltaOperation` objects (currently TAG-only).
- **OfflineAdapter**: Iterates dataset → generator → evaluator → reflector → curator → playbook apply.
- **OnlineAdapter**: Per-event orchestration; can reuse an existing generator result or invoke GeneratorRole on demand.
- **EnvironmentEvaluator**: Pluggable protocol returning verdicts/metrics used by the reflector.

## Playbook Operations
- **ADD**: create or upsert a bullet with section (auto-creates section if missing).
- **UPDATE**: change content/section/metadata of an existing bullet.
- **TAG**: increment/decrement helpful/harmful counters (aggregates duplicate TAG operations).
- **REMOVE**: delete a bullet.
- All delta batches execute transactionally; revisions store applied operations for audit and rollback workflows.

## How to Extend
- Add new prompts or schemas: update `prompts.py` and role parsers.
- Add new API endpoints: extend `controllers/playbook.py` and export in `urls.py`.
- Expose playbook data to agents: adjust `AceOrchestrator.build_context_block` or sorting logic.
- Integrate richer environment signals: implement an `EnvironmentEvaluator` and inject into adapters.
- Add rollback tooling: build on `AcePlaybookRevision` to apply inverse deltas.

## Testing
- Unit suites under `tests/unit/ace` cover deltas, orchestrator behavior, playbook lifecycle, and adapters (LLM + evaluator stubs).
- When running locally without libpq/postgres, disable `pytest_databases` plugins:
  - `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 uv run pytest tests/unit/ace --quiet -p no:pytest_databases.docker -p no:pytest_databases.docker.postgres`

## Operational Notes
- Keep `AI_ENABLE_ACE` off for tenants until you have vetted strategies and monitoring.
- Use `/ace/playbook/revisions` to audit changes; couple with log aggregation for who/when.
- Ensure production migrations are applied (`uv run app database upgrade`) before enabling ACE.
- If agents omit ACE tags in responses, the orchestrator still attributes feedback to injected IDs; encourage tag usage via prompts for better causality.
