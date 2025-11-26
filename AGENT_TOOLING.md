# Agent Tool Implementation

This project uses the OpenAI Agents SDK with a dedicated tool stack for todo management. The tool implementations are now grouped into three modules so each agent can focus on a smaller, purpose-built surface area.

## Tool Modules

- `src/app/domain/todo_agents/tools/todo_crud_tools.py` — create, update, and delete todo items, including tag handling and conflict checks.
- `src/app/domain/todo_agents/tools/todo_schedule_tools.py` — search and scheduling helpers (`get_todo_list`, `analyze_schedule`, `schedule_todo`, `batch_update_schedule`) plus the supporting utilities they need.
- `src/app/domain/todo_agents/tools/todo_support_tools.py` — supporting tools that are not CRUD or scheduling focused (currently quota lookups).
- Shared wiring lives in `tool_definitions.py` (FunctionTool registration), `tool_context.py` (service accessors), and `system_instructions.py` (agent system prompt).

Each file can back a dedicated agent: one agent for CRUD, one for scheduling/search, and one for supporting actions. You can also continue to expose the combined tool list via `get_tool_definitions()` when you need a single, full-featured agent.

## Available Agents

- Full agent: `get_todo_agent()` uses `get_tool_definitions()` for the entire tool stack.
- CRUD agent: `get_todo_crud_agent()` with `get_crud_tool_definitions()` (create, update, delete; includes `get_user_datetime`).
- Schedule/search agent: `get_todo_schedule_agent()` with `get_schedule_tool_definitions()` (`get_todo_list`, `analyze_schedule`, `schedule_todo`, `batch_update_schedule`; includes `get_user_datetime`).
- Support agent: `get_todo_support_agent()` with `get_support_tool_definitions()` (`get_user_quota`; includes `get_user_datetime` and any future auxiliary tools).

Example:

```python
from app.domain.todo_agents.tools import get_todo_schedule_agent
from agents import Runner

agent = get_todo_schedule_agent()
result = await Runner.run(agent, "Find me a free slot for a 45-minute study block tomorrow")
```

API tip: the todo agent endpoints accept `agent_name` (defaults to `TodoAssistant`) so you can route streaming or standard requests to `TodoCrudAssistant`, `TodoScheduleAssistant`, or `TodoSupportAssistant` without breaking existing clients. See `docs/AGENT_TOOLS_ARCHITECTURE_GUIDE.md` for details.

## How Tools Are Registered

Tools are registered in `tool_definitions.py` using the Agents SDK `FunctionTool` wrapper. The definitions import implementations from the three modules above, so adding or relocating a tool only requires updating its import target and `FunctionTool` entry.

Example pattern:

```python
create_todo_tool = FunctionTool(
    name="create_todo",
    description="Create a new todo item using the TodoService.",
    params_json_schema=CreateTodoArgs.model_json_schema(),
    on_invoke_tool=create_todo_impl,
)
```

If you want separate agents per category, build agent-specific tool lists by selecting only the functions you need from each module before constructing the agent.

## Implementation Notes

- Argument preprocessing for double-encoded arrays (e.g., `tags`) lives in `todo_crud_tools._preprocess_args` and is reused by the scheduling module.
- Time parsing helpers keep everything timezone-aware and validate conflict checks through `TodoService`.
- Scheduling helpers use `TodoService` and `TagService` to suggest optimal slots, list todos, and apply batch updates while guarding against conflicts.
- Quota checks run through `get_user_quota_impl`, which calls the rate limit and quota services injected via `tool_context`.

## Adding a New Tool

1. Pick the target module (CRUD, scheduling/search, or support) and implement an `*_impl` function there.
2. Define a matching Pydantic argument model in `argument_models.py`.
3. Export the tool in `tool_definitions.py` by adding a `FunctionTool` entry that references your implementation and JSON schema.
4. When creating new agents, assemble the tool list you need (full set or category-specific) and wire it into the Agents SDK runner.
