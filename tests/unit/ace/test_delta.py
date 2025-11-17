from __future__ import annotations

import pytest

from app.domain.ace.delta import DeltaAction, DeltaOperation


def test_add_operation_requires_content_and_section() -> None:
    with pytest.raises(ValueError):
        DeltaOperation(action=DeltaAction.ADD, bullet_id="s1")


def test_update_operation_requires_fields() -> None:
    with pytest.raises(ValueError):
        DeltaOperation(action=DeltaAction.UPDATE, bullet_id="s1")


def test_tag_operation_requires_deltas() -> None:
    with pytest.raises(ValueError):
        DeltaOperation(action=DeltaAction.TAG, bullet_id="s1")


def test_valid_operations_pass_validation() -> None:
    add = DeltaOperation(
        action=DeltaAction.ADD,
        bullet_id="s1",
        section_name="core",
        content="Always confirm deadlines.",
    )
    assert add.section_name == "core"

    update = DeltaOperation(
        action=DeltaAction.UPDATE,
        bullet_id="s1",
        content="Updated text",
    )
    assert update.content == "Updated text"

    tag = DeltaOperation(
        action=DeltaAction.TAG,
        bullet_id="s1",
        helpful_delta=2,
    )
    assert tag.helpful_delta == 2
