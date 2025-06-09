from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = pytest.mark.anyio


async def test_todo_list(client: "AsyncClient", superuser_token_headers: dict[str, str]) -> None:
    response = await client.get("/api/todos", headers=superuser_token_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) > 0


async def test_todo_create(client: "AsyncClient", superuser_token_headers: dict[str, str]) -> None:
    response = await client.post(
        "/api/todos",
        json={"title": "Test Todo", "description": "This is a test todo item."},
        headers=superuser_token_headers,
    )
    assert response.status_code == 201
    assert response.json()["title"] == "Test Todo"


async def test_todo_get(client: "AsyncClient", superuser_token_headers: dict[str, str]) -> None:
    response = await client.get("/api/todos/7b3cfad7-6772-4fb2-a550-c12d9771cd30", headers=superuser_token_headers)
    assert response.status_code == 200
    assert response.json()["id"] == "7b3cfad7-6772-4fb2-a550-c12d9771cd30"


async def test_todo_update(client: "AsyncClient", superuser_token_headers: dict[str, str]) -> None:
    response = await client.patch(
        "/api/todos/7b3cfad7-6772-4fb2-a550-c12d9771cd30",
        json={"title": "Updated Todo",
              "description": "This todo has been updated."},
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Updated Todo"
    assert response.json()["description"] == "This todo has been updated."


async def test_todo_delete(client: "AsyncClient", superuser_token_headers: dict[str, str]) -> None:
    response = await client.delete("/api/todos/7b3cfad7-6772-4fb2-a550-c12d9771cd30", headers=superuser_token_headers)
    assert response.status_code == 204
