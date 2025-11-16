# ACE Framework Product Requirements Document

## 1. Overview
**Product Name:** ACE (Agentic Context Engineering) Framework  
**Document Owner:** AI Platform Team  
**Revision:** v0.1 (Draft)  
**Last Updated:** 2025-11-16

The ACE Framework introduces an adaptive, multi-agent learning loop for the Litestar Todo backend. It augments the existing AI agent by enabling generator, reflector, and curator roles to iteratively improve prompt/playbook strategies through structured feedback. ACE targets both offline pre-training and online continual learning workflows, unlocking transparent, auditable decision making and faster convergence on high-quality responses.

## 2. Background & Motivation
- The current Todo agent relies on static system instructions and hand-authored best practices. Updates are manual, error prone, and hard to validate.
- As usage scales, we need mechanisms to track which strategies drive success, quickly retire harmful advice, and personalize agent behavior per user/team.
- Multi-turn agent sessions already exist; however, there is no automated loop to reflect on outcomes, adapt the playbook, or measure the impact of changes.
- The ACE Framework addresses these gaps by introducing a structured playbook repository and autonomous adaptation cycles that keep the agent aligned with evolving tasks and feedback.

## 3. Goals & Non-Goals
### Goals
1. Provide a production-ready framework for Generator → Reflector → Curator loops with persistent playbook storage and telemetry.  
2. Allow both offline batch training and online incremental updates of strategy bullets without human-in-the-loop for each change.  
3. Ensure every generator response cites explicit strategy IDs to maintain traceability.  
4. Deliver configuration toggles to enable/disable ACE per deployment environment without disturbing the legacy agent flow.  
5. Supply comprehensive documentation, tests, and observability for confident rollout and future extensibility.

### Non-Goals
- Designing or delivering new end-user UI for editing the playbook.  
- Implementing advanced personalization models beyond shared playbook evolution.  
- Shipping a general-purpose AutoML framework; ACE focuses on agent prompt/strategy management.  
- Replacing existing rate limiting, quota, or security primitives (these are leveraged, not rewritten).

## 4. Target Personas
| Persona | Needs | Level of Interaction |
| --- | --- | --- |
| **AI Ops Engineer** | Monitor strategy evolution, rollback harmful deltas, analyze metrics | High |
| **Backend Developer** | Integrate ACE toggles, extend ACE services, write unit/integration tests | High |
| **Product Manager** | Understand impact on task success, plan phased rollout | Medium |
| **Support Engineer** | Investigate session outcomes with causal references | Medium |

## 5. User Stories
1. *As an AI Ops engineer, I want to view the latest playbook bullets and their helpful/harmful counts so I can assess strategy quality.*  
2. *As a backend developer, I want the generator outputs to list referenced strategies so I can debug decision paths.*  
3. *As a product manager, I want a feature flag to turn ACE on/off per environment to manage rollout risk.*  
4. *As an AI Ops engineer, I want to run an offline training job on historical transcripts to bootstrap the playbook before production traffic.*  
5. *As a support engineer, I want to inspect session history annotated with ACE reflections to explain outcomes to users.*

## 6. Functional Requirements
### 6.1 Architecture & Domain
- Create `src/app/domain/ace` with modules: `roles.py`, `playbook.py`, `delta.py`, `adaptation.py`, `llm.py`, `prompts.py`, plus supporting schemas/controllers/services.  
- Register the domain with Litestar routing, dependency injection, and exports.

### 6.2 Playbook Model & Storage
- Define SQLAlchemy models `AcePlaybookBullet`, `AcePlaybookSection`, and `AcePlaybookRevision` (for audit trail).  
- Each bullet contains: `id (str)`, `content`, `section`, `helpful_count`, `harmful_count`, `metadata JSON`, timestamps.  
- Maintain unique bullet IDs and allow many-to-one mapping with sections.
- Provide service methods for retrieving playbook snapshots, applying deltas atomically, and rolling back revisions.

### 6.3 Roles & Workflow
- Implement `GeneratorRole` calling the existing agent runner, capturing reasoning trace, final answer, and referenced strategies.  
- Implement `ReflectorRole` that evaluates generator output versus environment feedback/ground truth to determine success factors and classify strategies.  
- Implement `CuratorRole` converting reflections into delta operations (ADD/UPDATE/TAG/REMOVE).  
- Support environment feedback interfaces for offline batch datasets and live traffic heuristics.

### 6.4 Adaptation Pipelines
- `OfflineAdapter`: iterate over training dataset (epochs, batching), apply adaptation cycles, collect metrics, and commit playbook deltas in batches.  
- `OnlineAdapter`: triggered per new sample, update playbook immediately (transactional) and refresh caches.  
- Provide CLI entry points (e.g., `manage.py ace-offline-train`).

### 6.5 Integration with Todo Agent
- Extend `TodoAgentService` with ACE orchestration, controlled by new setting `settings.ai.enable_ace`.  
- When enabled, generator stage should insert active strategies into prompts dynamically and record tool traces.  
- Reflector should use agent session + environment signals (initial heuristic: success if final message not error and user confirms).  
- Curator applies deltas after each interaction, adjusting helpful/harmful counters and caching updates.  
- Ensure fallback to current behavior when ACE is disabled.

### 6.6 APIs & Operations
- Provide REST endpoints for playbook inspection (`GET /ace/playbook`), delta submission (`POST /ace/playbook/deltas`), and revision history (`GET /ace/playbook/revisions`).  
- Reuse authentication/authorization guards (JWT).  
- Extend `SessionMessage.extra_data` to record ACE metadata (strategy IDs, reflection results).  
- Implement logging + metrics for every adaptation cycle (success/failure, delta size, response latency).

## 7. Non-Functional Requirements
| Category | Requirement |
| --- | --- |
| **Performance** | ACE-enabled response latency should not exceed baseline by >15% P99; provide async execution to prevent blocking requests. |
| **Scalability** | Support playbook size up to 5k bullets with efficient caching and pagination. |
| **Reliability** | Delta application must be transactional with rollback capability; provide at-least-once retry semantics without duplicate mutations. |
| **Security** | Apply existing auth/role guards; ensure no PII leaks via playbook content; sanitize manual delta submissions. |
| **Observability** | Emit structlog context fields (`ace.strategy_ids`, `ace.cycle_id`), Prometheus counters for helpful/harmful tags, and success/failure counts. |
| **Testability** | Include unit tests for playbook operations and role prompts; integration tests for end-to-end cycle under both offline & online adapters. |
| **Maintainability** | Follow existing domain architecture patterns; document configuration, CLI commands, and operational playbooks. |

## 8. Success Metrics
- ≥80% of generator responses cite at least one strategy ID when ACE enabled.  
- ≥50% reduction in manual prompt updates over three release cycles.  
- Logged harmful strategy count decreases by ≥30% after one month of ACE online learning.  
- No increase in support tickets attributed to AI agent hallucinations.  
- Mean time to rollback a harmful playbook change < 10 minutes.

## 9. Dependencies & Risks
### Dependencies
- Existing Litestar agent infrastructure (Runner, SQLiteSession).  
- Database migration pipeline (Alembic).  
- Observability stack (structlog, metrics exporters).  
- Access to training datasets and environment evaluation signals.

### Risks & Mitigations
| Risk | Impact | Mitigation |
| --- | --- | --- |
| Incorrect environment feedback leading to harmful deltas | Degraded agent quality | Start with conservative heuristics, gate curator actions behind confidence thresholds, add manual approval workflow if needed. |
| Increased latency | Poor UX | Introduce async adapters and caching; allow ACE to run asynchronously post-response if needed. |
| Data drift or runaway harmful strategies | Trust erosion | Add revision audit trail, configurable auto-revert thresholds, manual delta APIs. |
| Complex rollout | Deployment delays | Provide feature flag, staged rollout plan, and monitoring dashboards before enabling globally. |

## 10. Rollout Strategy
1. **Phase 0 – Development:** Implement ACE components under feature flag; run unit/integration tests.  
2. **Phase 1 – Internal Offline Training:** Bootstrap playbook using historical data; validate metrics offline.  
3. **Phase 2 – Internal Beta (Online):** Enable ACE for selected internal users, monitor metrics closely, refine heuristics.  
4. **Phase 3 – Gradual External Rollout:** Enable for subsets of production users, progressively increase coverage, keep rollback option ready.  
5. **Phase 4 – General Availability:** ACE enabled by default, continue to iterate on strategy templates and automation.

## 11. Open Questions
- What minimum dataset quality/format is required to reliably run the OfflineAdapter?  
- Should manual delta submissions require additional approvals or audit logging beyond revisions?  
- How do we expose ACE metrics in existing monitoring dashboards (Grafana/Splunk)?  
- Are there legal/compliance reviews needed for storing strategy metadata sourced from user feedback?  
- What thresholds should trigger automatic rollback of harmful strategies?

## 12. Appendices
- **Related Docs:** `docs/ACE_IMPLEMENTATION_PLAN.md`, `docs/AI_AGENT_ARCHITECTURE.md`, `docs/AGENT_SESSIONS_MANAGEMENT.md`.  
- **Terminology:**  
  - *Bullet:* A discrete playbook strategy entry.  
  - *Delta:* Atomic operation that adds, updates, tags, or removes a bullet.  
  - *Environment Feedback:* Signal representing real or simulated evaluation of agent output.  
  - *Cycle:* Generator → Reflector → Curator iteration.
