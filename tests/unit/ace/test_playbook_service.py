from __future__ import annotations

import pytest
from advanced_alchemy.base import UUIDAuditBase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.domain.ace.delta import DeltaAction, DeltaOperation
from app.domain.ace.playbook import AcePlaybookService

pytestmark = pytest.mark.anyio


@pytest.fixture()
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(UUIDAuditBase.registry.metadata.create_all)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)
    async with sessionmaker() as session:
        yield session
    await engine.dispose()


async def test_apply_full_delta_lifecycle(session: AsyncSession) -> None:
    service = AcePlaybookService(session=session)
    add_delta = DeltaOperation(
        action=DeltaAction.ADD,
        bullet_id="strat.deep_focus",
        section_name="foundations",
        section_display_name="Foundations",
        content="Confirm requirements, cite strategy IDs, and reflect on blockers.",
        metadata={"lang": "en"},
    )

    add_result = await service.apply_deltas([add_delta], applied_by="tester")
    assert add_result.added == ["strat.deep_focus"]
    assert add_result.revision_id is not None

    snapshot = await service.get_snapshot()
    assert "strat.deep_focus" in snapshot.bullets
    assert snapshot.sections["foundations"].bullet_ids == ["strat.deep_focus"]

    update_delta = DeltaOperation(
        action=DeltaAction.UPDATE,
        bullet_id="strat.deep_focus",
        content="Confirm requirements before coding.",
        metadata={"lang": "en", "version": 2},
    )

    update_result = await service.apply_deltas([update_delta], applied_by="tester")
    assert update_result.updated == ["strat.deep_focus"]

    snapshot = await service.get_snapshot()
    bullet = snapshot.bullets["strat.deep_focus"]
    assert bullet.content == "Confirm requirements before coding."
    assert bullet.metadata["version"] == 2

    tag_delta = DeltaOperation(
        action=DeltaAction.TAG,
        bullet_id="strat.deep_focus",
        helpful_delta=3,
        harmful_delta=-1,
    )

    tag_result = await service.apply_deltas([tag_delta], applied_by="tester")
    assert tag_result.tagged == ["strat.deep_focus"]

    snapshot = await service.get_snapshot()
    bullet = snapshot.bullets["strat.deep_focus"]
    assert bullet.helpful_count == 3
    assert bullet.harmful_count == 0  # floor at zero

    remove_delta = DeltaOperation(
        action=DeltaAction.REMOVE,
        bullet_id="strat.deep_focus",
    )

    remove_result = await service.apply_deltas([remove_delta], applied_by="tester")
    assert remove_result.removed == ["strat.deep_focus"]

    snapshot = await service.get_snapshot()
    assert "strat.deep_focus" not in snapshot.bullets


async def test_apply_deltas_deduplicates_tags(session: AsyncSession) -> None:
    service = AcePlaybookService(session=session)
    await service.apply_deltas(
        [
            DeltaOperation(
                action=DeltaAction.ADD,
                bullet_id="strat.handles_dup",
                section_name="ops",
                content="Always log idempotency keys.",
            )
        ],
        applied_by="tester",
    )

    tag_ops = [
        DeltaOperation(
            action=DeltaAction.TAG,
            bullet_id="strat.handles_dup",
            helpful_delta=1,
        ),
        DeltaOperation(
            action=DeltaAction.TAG,
            bullet_id="strat.handles_dup",
            helpful_delta=2,
        ),
    ]
    result = await service.apply_deltas(tag_ops, applied_by="tester")
    assert result.tagged == ["strat.handles_dup"]
    snapshot = await service.get_snapshot()
    assert snapshot.bullets["strat.handles_dup"].helpful_count == 3
