"""URL constants for agent_sessions domain."""

# Base path for the domain
AGENT_SESSIONS_BASE = "/api/agent-sessions"

# CRUD operations for agent sessions
AGENT_SESSIONS_LIST = f"{AGENT_SESSIONS_BASE}"
AGENT_SESSIONS_CREATE = f"{AGENT_SESSIONS_BASE}"
AGENT_SESSIONS_DETAIL = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}"
AGENT_SESSIONS_UPDATE = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}"
AGENT_SESSIONS_DELETE = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}"

# Session message operations
SESSION_MESSAGES_LIST = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/messages"
SESSION_MESSAGES_CREATE = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/messages"
SESSION_MESSAGES_DETAIL = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/messages/{{message_id:uuid}}"
SESSION_MESSAGES_DELETE = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/messages/{{message_id:uuid}}"

# Session management operations
SESSION_ACTIVATE = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/activate"
SESSION_DEACTIVATE = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/deactivate"
SESSION_CLEAR_MESSAGES = f"{AGENT_SESSIONS_BASE}/{{session_id:uuid}}/clear-messages"

# Conversation endpoint
SESSION_CONVERSATION = f"{AGENT_SESSIONS_BASE}/conversation"
