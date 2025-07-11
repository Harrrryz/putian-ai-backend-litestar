from agents import Agent, OpenAIChatCompletionsModel, function_tool
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

import app.db.models as m
from app.db.models.importance import Importance
from app.db.session import async_session
from app.domain.todo.schemas import TagCreate, TagModel, TodoCreate, TodoModel


class CreateTodoDto(BaseModel):
    todo_name: str = Field(
        ...,
        description="The name of the todo to create"
    )
    tags: list[str] = Field(
        ...,
        description="The tags of the todo to create, pick from the list of tags available first, if not suitable, create new tags appropriately"
    )
    planned_date: str = Field(
        ...,
        description="The planned date of the todo to create it should be in the format YYYY-MM-DD HH:MM:SS"
    )
    content: str = Field(
        ...,
        description="The content of the todo to create"
    )
    importance: Importance = Field(
        default=Importance.NONE,
        description="The importance of the todo to create, if the user does not specify it, it will be set to NONE"
    )


@function_tool
async def create_todo(create_todo_dto: CreateTodoDto) -> m.Todo:
    todo = m.Todo(
        todo_name=create_todo_dto.todo_name,
        tags=[m.Tag(tag_name=tag) for tag in create_todo_dto.tags],
        planned_date=create_todo_dto.planned_date,
        content=create_todo_dto.content,
        importance=create_todo_dto.importance,
        user_id=1,  # Assuming user_id is 1 for the sake of example
    )
    async with async_session() as session:
        session.add(todo)
        await session.commit()
        await session.refresh(todo)
    return todo


SYSTEM_INSTRUCTIONS = f"You are a todo list assistant, you can create a todo by providing the todo name, tags, planned date, content and importance. If the user does not provide enough information, ask for it. If the user doesn't provide content, importance or tags, you can create from the user's given information. The default importance is 0. If the user doesn't provide tags, you should create appropriate tags for user, the common tags can be 'study', 'entertainment', 'work' etc.. Today is {datetime.now().strftime('%Y-%m-%d')}."

load_dotenv('.env', override=True)
model = OpenAIChatCompletionsModel(model='doubao-1.5-pro-32k-250115',
                                   openai_client=AsyncOpenAI(
                                       api_key=os.getenv('VOLCENGINE_API_KEY'),
                                       base_url=os.getenv(
                                           'VOLCENGINE_BASE_URL'),
                                   ))
agent = Agent(name="Assistant", instructions=SYSTEM_INSTRUCTIONS,
              model=model, tools=[create_todo])
