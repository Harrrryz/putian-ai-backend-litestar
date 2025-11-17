# ACE Framework PRD

## 1. Overview
- **Initiative**: Introduce the ACE (Agentic Context Engineering) framework to evolve the todo agent stack through Generator → Reflector → Curator learning loops and a persistent playbook.
- **Objective**: Deliver adaptive, traceable agent responses that continuously learn from environment feedback, while remaining optional and backwards compatible with the current Litestar todo agents.
- **Scope**: New ACE domain package, playbook persistence, role orchestration, adaptation pipelines (offline/online), feature-flagged todo agent integration, APIs, tooling, documentation, and tests.

## 2. Background & Problem Statement
- Existing todo agents lack a structured mechanism to capture reasoning strategies, evaluate their outcomes, and iteratively improve, leading to brittle behaviors and opaque decision trails.
- Teams need durable knowledge (playbook bullets) grounded in production data, the ability to attribute success/failure to strategies, and tooling to roll forward/back strategies without risking regressions.

## 3. Goals
1. Ship a modular ACE package (`src/app/domain/ace`) with Generator, Reflector, Curator roles backed by a transactional playbook store and LLM abstraction.
2. Support both offline training loops for dataset-driven learning and online loops for real-time adaptation.
3. Integrate ACE seamlessly with existing todo agents via feature flags, enabling citation of playbook strategies and recording causal chains in session history.
4. Provide operators APIs/CLIs to inspect, update, and rollback playbook knowledge with auditability.
5. Maintain observability, testing, and documentation parity with the rest of the codebase.

## 4. Non-Goals
- Replacing the current todo agent execution pipeline entirely (ACE augments it behind a flag).
- Building new UI surfaces; endpoints supply data for future dashboards but UI work is deferred.
- Creating proprietary LLM providers; ACE consumes existing adapters (OpenAI, Anthropic, local).

## 5. Stakeholders & Personas
- **Product/AI Lead**: Defines learning objectives, monitors success metrics, approves strategy changes.
- **Applied Researchers**: Run offline training, tweak prompts, analyze reflections, curate deltas.
- **Backend Engineers**: Implement ACE services, migrations, and ensure reliability/performance.
- **Ops/Support**: Needs observability, rollback tools, and documentation to manage production incidents.
- **End Users**: Receive higher quality, explainable agent responses (indirect stakeholders).

## 6. User Stories & Use Cases
1. As an AI lead, I can review Generator outputs with referenced strategy IDs and understand why an answer was produced.
2. As a researcher, I can replay historical datasets through OfflineAdapter, producing updated playbook bullets and metrics.
3. As a backend engineer, I can enable ACE for select tenants, ensuring legacy behavior remains unchanged when disabled.
4. As an ops engineer, I can inspect the ACE playbook via API, apply manual delta operations, and rollback harmful updates.
5. As a product analyst, I can read structured reflections that classify strategies as helpful/harmful/neutral for a session.
6. As an integration tester, I can verify that ACE-enabled flows tag strategy usage in `SessionMessage.extra_data`.

## 7. Functional Requirements

### 7.1 Foundation & Domain Scaffolding
- Create `src/app/domain/ace` mirroring the domain layout with `roles.py`, `playbook.py`, `delta.py`, `adaptation.py`, `llm.py`, `prompts.py`, controllers, schemas, and services.
- Wire new modules into package exports, dependency containers, and routing (Litestar controllers).
- Follow repo coding standards (type hints, Ruff rules, domain boundaries).

### 7.2 Playbook Persistence Layer
- Define SQLAlchemy models (`AcePlaybookBullet`, `AcePlaybookSection`, potentially `AcePlaybookRevision`) with helpful/harmful counters, metadata JSON, timestamps, section ordering, and unique bullet IDs.
- Generate Alembic migrations with indices on `(section, created_at)` and section/bullet foreign keys.
- Implement repository/service classes enabling CRUD, ordered reads, and atomic delta operations (`ADD`, `UPDATE`, `TAG`, `REMOVE`) with idempotency and de-duplication.
- Persist audit logs/journals for rollback and expose API/service helpers to revert revisions.

### 7.3 LLM Abstraction & Prompt Engine
- Create `LLMClient` interface with async `generate`, retries, timeouts, and observability hooks (structlog, optional Opik trace IDs).
- Provide adapters for existing providers (litellm/OpenAI) and plug-in support for future ones.
- Author versioned prompt templates + JSON schema contracts in `ace/prompts.py`, referencing domain context and enabling multilingual error messages.

### 7.4 Role Implementations
- Implement `GeneratorRole`, `ReflectorRole`, `CuratorRole` in `roles.py` with Pydantic IO models capturing reasoning traces, verdicts, and delta requests.
- Generator: accepts questions, context, playbook sections, prior reflections, and returns reasoning + final answer + strategy IDs.
- Reflector: ingests generator trace, environment verdict/ground truth, classifies strategy helpfulness, and outputs root-cause insights + tags.
- Curator: transforms reflections into normalized `DeltaOperation` objects that update counts or content with deduplication safeguards.

### 7.5 Adaptation Pipelines
- Build `OfflineAdapter` (dataset loop, batched commits) and `OnlineAdapter` (real-time) orchestrations coordinating Generator → environment evaluation → Reflector → Curator → Playbook updates.
- Support pluggable environment evaluators (sync/async), retry policies, metrics, and cancellation.
- Provide CLI/SDK entry points to run adapters and track progress.

### 7.6 Todo Agent Integration
- Introduce an `AceOrchestrator` (or similar helper) in `todo_agents` service layer to invoke ACE roles when flags/settings enable it.
- Hydrate playbook snippets and inject into generator prompts via `tool_context`/`system_instructions`.
- Capture tool traces, reflect on environment feedback (initial heuristics using existing success signals), and update playbook accordingly.
- Ensure ACE-disabled flows remain unchanged; add configuration toggles in settings/env.

### 7.7 Delta Application & Rollback
- In `playbook.py`, apply curator deltas inside database transactions with rollback journals.
- Expose CLI/service endpoints for listing revisions, reverting updates, and flushing caches.
- Surface helpful/harmful counters to support pruning or boosting strategies.

### 7.8 APIs & Session Storage
- Add Litestar controllers under `/ace/playbook` for listing playbooks, submitting deltas, and viewing metrics, protected by existing auth/permission checks.
- Extend `agent_sessions` services/models to record ACE metadata (strategy IDs, reflections, verdicts) in `SessionMessage.extra_data` to preserve causal chains.
- Provide endpoints or hooks for retrieving per-session ACE summaries.

### 7.9 Offline Training Tooling
- Add CLI commands (e.g., `manage.py ace-offline-train` or uv scripts) to run OfflineAdapter jobs with dataset paths/configs, checkpointing, and metrics output.
- Document dataset schema and provide sample fixtures/tests.

### 7.10 Configuration & Settings
- Extend `src/app/config/base.py`, `.env.sample`, and related constants with ACE toggles, provider aliases, dataset paths, retry/timeouts, and metric settings.
- Ensure configuration is injectable/testable through dependency providers.

### 7.11 Testing & Observability
- Create `tests/unit/ace` for roles, deltas, playbook services, and prompt serialization.
- Extend integration tests to cover ACE-enabled todo agent flows using stub LLMs/environments.
- Maintain regression tests for migrations and baseline behavior when ACE is disabled.
- Instrument roles/adapters with structlog context (session_id, strategy_ids) and metrics counters (Prometheus hooks, rate-limit interplay).

### 7.12 Documentation & Developer Workflow
- Author `docs/ACE_FRAMEWORK.md`, update `WIKI_TOC.md`, and cross-link from AI agent guides.
- Document setup instructions, configuration, operational procedures, troubleshooting, and release management.
- Update Makefile/CI targets if new commands are introduced and ensure `pre-commit` stays green.

## 8. Non-Functional Requirements
- **Reliability**: Delta applications must be atomic and recoverable; adapters must handle retries/backoff.
- **Scalability**: Playbook queries and updates must support concurrent sessions without contention (appropriate indices, transactions).
- **Security & Compliance**: Reuse existing auth/permissions; ensure no secrets logged in prompts; respect rate limits/quota services.
- **Observability**: All role executions emit structured logs/metrics for debugging and analytics.
- **Maintainability**: Code organized by domain boundaries, fully typed, with clear APIs and docs for future contributors.

## 9. Technical Approach Summary
1. Scaffold ACE domain modules and migrations following the implementation plan, ensuring wiring into dependency injection and router tables.
2. Implement playbook persistence + delta services first since they underpin the rest; include migrations and repositories.
3. Build LLM abstraction/prompt templates, followed by role classes using structured IO models.
4. Deliver adapters (offline/online) that orchestrate roles and integrate with environment evaluators and instrumentation.
5. Layer integration within `todo_agents`, gating via feature flags and ensuring session metadata captures strategy usage.
6. Add APIs/CLIs, configuration, observability hooks, and documentation, then complete the testing strategy.

## 10. Milestones
1. **M1 – Foundation & Persistence (Week 1-2)**: Domain scaffolding, models, migrations, playbook services, unit tests.
2. **M2 – Roles & LLM Layer (Week 3)**: LLM client, prompts, Generator/Reflector/Curator implementations with tests.
3. **M3 – Adaptation Pipelines (Week 4)**: Offline/online adapters, environment hooks, CLI integration.
4. **M4 – Todo Agent Integration (Week 5)**: Feature-flagged orchestration, session metadata, regression tests.
5. **M5 – APIs, Tooling, Docs (Week 6)**: Playbook endpoints, rollback tooling, observability, documentation updates.
6. **M6 – Stabilization (Week 7)**: End-to-end testing, performance tuning, production readiness checklist.

## 11. Success Metrics
- ≥20% improvement in task success rate for ACE-enabled cohorts during A/B test.
- ≥80% of Generator responses cite at least one playbook strategy ID.
- Reflections correctly classify strategy helpfulness with ≥90% agreement against manual review.
- Zero regression in baseline todo agent functionality when ACE is disabled (all existing tests pass).
- Playbook rollback operations complete <1s on P95 workloads.

## 12. Risks & Mitigations
- **LLM variability**: Mitigate with structured prompts, retries, and offline evaluation suites.
- **Data drift & harmful strategies**: Address via helpful/harmful counters, curator deduplication, and rollback tooling.
- **Performance overhead**: Use feature flags, caching playbook slices, and asynchronous adapters to limit latency.
- **Complex migrations**: Provide thorough Alembic migration tests and backward-compatible schema changes.
- **Operational complexity**: Deliver clear documentation, Makefile targets, and observability hooks for fast incident response.

## 13. Open Questions
1. What initial heuristic/environment feedback will signal success vs. failure in the online adapter (e.g., HTTP 200, tool-specific checks)?
2. Which dataset formats and storage locations will OfflineAdapter consume (S3, local files, DB exports)?
3. Do we require a multi-tenant playbook partitioning strategy on day one, or can we scope to single tenant?
4. What thresholds trigger automatic removal vs. manual review for harmful strategies?

## 14. References
- `ace-docs/ACE-REQUIREMENTS.md`
- `ace-docs/ACE-IMPLEMENTATION-PLAN.md`
- `docs/AI_AGENT_ARCHITECTURE.md`
- `docs/AGENT_SESSIONS_MANAGEMENT.md`
- `docs/TOOL_DEFINITION_SYSTEM.md`
