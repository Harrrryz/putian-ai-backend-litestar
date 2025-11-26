# Todo Agent Tools & Routing

This guide explains how the todo agent tools are organized and how to select different agents in the API.

## Tool Modules

- **CRUD** — `src/app/domain/todo_agents/tools/todo_crud_tools.py` (create, update, delete; tag management and conflict checks).
- **Scheduling/Search** — `src/app/domain/todo_agents/tools/todo_schedule_tools.py` (`get_todo_list`, `analyze_schedule`, `schedule_todo`, `batch_update_schedule`).
- **Support** — `src/app/domain/todo_agents/tools/todo_support_tools.py` (quota lookups and future supporting tools).

Shared wiring lives in `tool_definitions.py` (FunctionTool registration), `tool_context.py` (service injection), and `agent_factory.py` (agent builders).

## Agent Variants

The default agent remains `TodoAssistant` and exposes the full tool set. Three specialized agents are also available:

- `TodoCrudAssistant` — CRUD-only surface (includes `get_user_datetime`).
- `TodoScheduleAssistant` — scheduling/search surface (includes `get_user_datetime`).
- `TodoSupportAssistant` — support/auxiliary surface (`get_user_quota`, includes `get_user_datetime`).

Builders live in `agent_factory.py`:

- `get_todo_agent()` — default, full tool set.
- `get_todo_crud_agent()`, `get_todo_schedule_agent()`, `get_todo_support_agent()` — specialized agents.
- `get_agent_by_name(name)` — helper that returns the requested agent or falls back to `TodoAssistant`.

## API Usage

The todo agent endpoints accept an optional `agent_name` field (defaults to `TodoAssistant`) so you can route requests to a specific agent without breaking existing clients:

```json
{
  "messages": [{"role": "user", "content": "Find a free slot for a 30m workout tomorrow"}],
  "session_id": "user_123_schedule",
  "agent_name": "TodoScheduleAssistant"
}
```

Supported values: `TodoAssistant`, `TodoCrudAssistant`, `TodoScheduleAssistant`, `TodoSupportAssistant`.

## Adding Tools or Agents

1. Implement the tool in the appropriate module and add its argument model to `argument_models.py`.
2. Register it in `tool_definitions.py` so it is available to the full agent and to any subset you expose.
3. If a new agent surface is needed, add a builder to `agent_factory.py` and route to it via `agent_name` when calling the API.
