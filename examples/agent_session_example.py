"""Example usage of DatabaseSession with OpenAI Agents SDK."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Note: This is an example. Actual imports would depend on your OpenAI Agents SDK setup
# from agents import Agent, Runner
from app.lib.database_session import DatabaseSession


async def example_agent_conversation(db_session: AsyncSession, user_id: str) -> None:
    """Example of using DatabaseSession with OpenAI Agents SDK.

    Args:
        db_session: Database session for persistence
        user_id: User ID for session ownership
    """
    # Create a database session for persistent conversation history
    session = DatabaseSession(
        session_id="conversation_123",
        user_id=user_id,
        db_session=db_session,
        agent_name="Assistant",
        agent_instructions="You are a helpful assistant.",
        session_name="Example Conversation",
    )

    # Example: Manually add some conversation history
    await session.add_items([
        {"role": "user", "content": "Hello! How are you?"},
        {"role": "assistant", "content": "Hello! I'm doing well, thank you for asking. How can I help you today?"},
    ])

    # Get conversation history
    history = await session.get_items()
    print("Current conversation history:")
    for item in history:
        print(f"{item['role']}: {item['content']}")

    # Example of using with OpenAI Agents SDK (when available):
    #
    # from agents import Agent, Runner
    #
    # agent = Agent(
    #     name="Assistant",
    #     instructions="You are a helpful assistant.",
    # )
    #
    # # Run agent with persistent session
    # result = await Runner.run(
    #     agent,
    #     "What's the weather like today?",
    #     session=session
    # )
    #
    # print(f"Agent response: {result.final_output}")

    # Example: Remove last message (for corrections)
    last_item = await session.pop_item()
    if last_item:
        print(f"Removed: {last_item['role']}: {last_item['content']}")

    # Example: Clear entire session
    # await session.clear_session()


async def example_session_management(db_session: AsyncSession, user_id: str) -> None:
    """Example of advanced session management features."""

    session = DatabaseSession(
        session_id="advanced_session",
        user_id=user_id,
        db_session=db_session,
    )

    # Add messages with tool call information
    await session.add_items([
        {"role": "user", "content": "Can you calculate 2 + 2?"},
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "calculator",
                        "arguments": '{"operation": "add", "a": 2, "b": 2}'
                    }
                }
            ]
        },
        {
            "role": "tool",
            "tool_call_id": "call_123",
            "name": "calculator",
            "content": "4"
        },
        {"role": "assistant", "content": "The result of 2 + 2 is 4."}
    ])

    # Update session metadata
    await session.update_session_metadata(
        session_name="Calculator Session",
        agent_name="Math Assistant",
        agent_instructions="You are a helpful math assistant.",
    )

    # Get recent conversation (limit to last 2 messages)
    recent_items = await session.get_items(limit=2)
    print("Recent conversation:")
    for item in recent_items:
        print(f"{item['role']}: {item['content']}")


def create_session_factory(db_session_factory):
    """Factory function to create DatabaseSession instances.

    This can be used as a dependency in your Litestar application.
    """
    def session_factory(session_id: str, user_id: str, **kwargs) -> DatabaseSession:
        return DatabaseSession(
            session_id=session_id,
            user_id=user_id,
            db_session=db_session_factory(),
            **kwargs
        )
    return session_factory


# Example integration with Litestar dependency injection
class AgentSessionService:
    """Service class for managing agent sessions."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db_session = db_session

    def create_session(
        self,
        session_id: str,
        user_id: str,
        agent_name: str | None = None,
        agent_instructions: str | None = None,
        session_name: str | None = None,
    ) -> DatabaseSession:
        """Create a new database session for OpenAI Agents SDK."""
        return DatabaseSession(
            session_id=session_id,
            user_id=user_id,
            db_session=self.db_session,
            agent_name=agent_name,
            agent_instructions=agent_instructions,
            session_name=session_name,
        )

    async def list_user_sessions(self, user_id: str) -> list[dict]:
        """List all sessions for a user."""
        from sqlalchemy.future import select
        from app.db.models import AgentSession

        stmt = select(AgentSession).where(AgentSession.user_id == user_id)
        result = await self.db_session.execute(stmt)
        sessions = result.scalars().all()

        return [
            {
                "id": str(session.id),
                "session_id": session.session_id,
                "session_name": session.session_name,
                "agent_name": session.agent_name,
                "is_active": session.is_active,
                "created_at": session.created_at,
                "updated_at": session.updated_at,
            }
            for session in sessions
        ]


# Example Litestar controller (pseudo-code)
"""
from litestar import Controller, post, get
from litestar.di import Provide

class AgentController(Controller):
    path = "/agents"
    
    @post("/sessions/{session_id}/chat")
    async def chat_with_agent(
        self,
        session_id: str,
        user_id: str,  # From JWT token or session
        message: str,
        agent_service: AgentSessionService = Provide(AgentSessionService),
    ) -> dict:
        # Create or get existing session
        session = agent_service.create_session(
            session_id=session_id,
            user_id=user_id,
            agent_name="Assistant",
            agent_instructions="You are a helpful assistant.",
        )
        
        # Use with OpenAI Agents SDK
        # agent = Agent(name="Assistant", instructions="...")
        # result = await Runner.run(agent, message, session=session)
        
        return {"response": "Agent response would go here"}
    
    @get("/sessions")
    async def list_sessions(
        self,
        user_id: str,  # From JWT token or session
        agent_service: AgentSessionService = Provide(AgentSessionService),
    ) -> list[dict]:
        return await agent_service.list_user_sessions(user_id)
"""


if __name__ == "__main__":
    # This would need actual database setup in practice
    print("DatabaseSession example - ready for OpenAI Agents SDK integration!")
