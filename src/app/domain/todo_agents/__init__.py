"""Todo agents domain."""

from .services import TodoAgentService, create_todo_agent_service
from .tools.agent_factory import get_todo_agent
from .tools.system_instructions import TODO_SYSTEM_INSTRUCTIONS
from .tools.tool_context import set_agent_context

__all__ = [
    # System instructions
    "TODO_SYSTEM_INSTRUCTIONS",
    # Services
    "TodoAgentService",
    "create_todo_agent_service",
    # Agent factory
    "get_todo_agent",
    # Context management
    "set_agent_context",
]

from . import controllers, deps, schemas, services, urls

__all__ = ("controllers", "deps", "schemas", "services", "urls")
