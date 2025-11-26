# Agent as Tools Implementation

This document describes the "Agent as Tools" pattern implemented in the Todo backend. This architecture allows a main agent (`TodoAssistant`) to act as an orchestrator, delegating complex tasks to specialized sub-agents (`SchedulingSpecialist`, `TodoCRUDAssistant`) by calling them as tools.

## Overview

The system uses a hierarchical multi-agent architecture:

1.  **Orchestrator Agent (`TodoAssistant`)**: The main entry point for user interaction. It understands the user's intent and delegates tasks to the appropriate specialist.
2.  **Specialized Agents**:
    *   **`SchedulingSpecialist`**: Handles all calendar analysis, conflict detection, and scheduling tasks.
    *   **`TodoCRUDAssistant`**: Handles creating, updating, deleting, and listing todo items.

## Architecture Components

### 1. Specialized Agents (`specialized_agents.py`)

We have defined factory functions to create specialized agents with restricted toolsets:

*   **`get_scheduling_agent()`**: Creates the `SchedulingSpecialist`.
    *   **Tools**: `analyze_schedule`, `schedule_todo`, `batch_update_schedule`, `get_todo_list`.
    *   **Instructions**: Focused on finding optimal time slots and managing the schedule.
*   **`get_crud_agent()`**: Creates the `TodoCRUDAssistant`.
    *   **Tools**: `create_todo`, `update_todo`, `delete_todo`, `get_todo_list`.
    *   **Instructions**: Focused on accurate data entry and management.

### 2. Orchestration Tools (`orchestration_tools.py`)

These are the "bridge" tools that the main agent uses to talk to the specialists. They wrap the sub-agent execution in a function tool.

*   **`consult_scheduler`**:
    *   **Input**: `ConsultSchedulerArgs` (contains a natural language `request`).
    *   **Behavior**: Instantiates the `SchedulingSpecialist` and runs it with the provided request.
    *   **Output**: The final response from the specialist.
*   **`consult_crud_agent`**:
    *   **Input**: `ConsultCrudAgentArgs` (contains a natural language `request`).
    *   **Behavior**: Instantiates the `TodoCRUDAssistant` and runs it with the provided request.
    *   **Output**: The final response from the specialist.

### 3. Main Agent Configuration (`agent_factory.py`)

The main `TodoAssistant` is now configured with:
*   **Orchestration Tools**: `consult_scheduler`, `consult_crud_agent`.
*   **Utility Tools**: `get_user_datetime`, `get_user_quota` (kept at the top level for context).
*   **Instructions**: `ORCHESTRATOR_INSTRUCTIONS` guide it to delegate tasks rather than doing them directly.

## Tool Organization

The tool implementations are organized by domain to support this architecture:

*   **`crud_tools.py`**: Core CRUD logic.
*   **`scheduling_tools.py`**: Scheduling and analysis logic.
*   **`utility_tools.py`**: Shared utilities.
*   **`orchestration_tools.py`**: The delegation logic.
*   **`tool_definitions.py`**: Exports grouped tool definitions (`get_crud_tools`, `get_scheduling_tools`) for the specialists.

## Request Flow Example

1.  **User**: "Find a time for my meeting with John and add it."
2.  **Orchestrator**:
    *   Analyzes request.
    *   Calls `consult_scheduler("Find a time for meeting with John")`.
3.  **Scheduling Specialist**:
    *   Calls `analyze_schedule`.
    *   Returns: "3:00 PM is free."
4.  **Orchestrator**:
    *   Receives "3:00 PM is free."
    *   Calls `consult_crud_agent("Create a meeting with John at 3:00 PM")`.
5.  **CRUD Assistant**:
    *   Calls `create_todo`.
    *   Returns: "Meeting created."
6.  **Orchestrator**:
    *   Returns final response to user: "I've scheduled your meeting with John for 3:00 PM."
