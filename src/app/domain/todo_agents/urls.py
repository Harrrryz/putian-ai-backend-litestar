"""URL constants for todo_agents domain."""

# Base path for the domain
TODO_AGENTS_BASE = "/api/todos"

# Agent operations
TODO_AGENTS_CREATE = f"{TODO_AGENTS_BASE}/agent-create"
TODO_AGENTS_SESSIONS = f"{TODO_AGENTS_BASE}/agent-sessions"
TODO_AGENTS_SESSION_HISTORY = f"{TODO_AGENTS_BASE}/agent-sessions/{{session_id:str}}/history"
TODO_AGENTS_CLEAR_SESSION = f"{TODO_AGENTS_BASE}/agent-sessions/{{session_id:str}}"
