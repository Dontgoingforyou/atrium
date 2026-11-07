from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models.portal_user_task_board_pref import PortalUserTaskBoardPref
from app.portal_collab.schemas.task import TaskBoardPrefRead, TaskBoardPrefWrite
from app.schemas.auth import UserPublic


def _empty_read() -> TaskBoardPrefRead:
    return TaskBoardPrefRead(
        column_order=[],
        hidden_status_keys=[],
        title_overrides={},
        subtasks_flat=False,
        hide_subtasks=False,
    )


def _row_to_read(row: PortalUserTaskBoardPref) -> TaskBoardPrefRead:
    return TaskBoardPrefRead(
        column_order=list(row.column_order or []),
        hidden_status_keys=list(row.hidden_status_keys or []),
        title_overrides=dict(row.title_overrides or {}),
        subtasks_flat=bool(row.subtasks_flat),
        hide_subtasks=bool(row.hide_subtasks),
    )


async def get_task_board_pref(session: AsyncSession, user: UserPublic) -> TaskBoardPrefRead:
    row = (
        await session.execute(select(PortalUserTaskBoardPref).where(PortalUserTaskBoardPref.user_sub == user.sub))
    ).scalar_one_or_none()
    if row is None:
        return _empty_read()
    return _row_to_read(row)


async def put_task_board_pref(
    session: AsyncSession,
    user: UserPublic,
    body: TaskBoardPrefWrite,
) -> TaskBoardPrefRead:
    row = (
        await session.execute(select(PortalUserTaskBoardPref).where(PortalUserTaskBoardPref.user_sub == user.sub))
    ).scalar_one_or_none()

    payload_order: list[str] = list(body.column_order)
    payload_hidden: list[str] = list(body.hidden_status_keys)
    payload_titles: dict[str, str] = dict(body.title_overrides)
    payload_flat = bool(body.subtasks_flat) and not bool(body.hide_subtasks)
    payload_hide = bool(body.hide_subtasks)

    if row is None:
        row = PortalUserTaskBoardPref(
            user_sub=user.sub,
            column_order=payload_order,
            hidden_status_keys=payload_hidden,
            title_overrides=payload_titles,
            subtasks_flat=payload_flat,
            hide_subtasks=payload_hide,
        )
        session.add(row)
        try:
            await session.flush()
        except IntegrityError:
            await session.rollback()
            row = (
                await session.execute(
                    select(PortalUserTaskBoardPref).where(PortalUserTaskBoardPref.user_sub == user.sub)
                )
            ).scalar_one()
            row.column_order = payload_order
            row.hidden_status_keys = payload_hidden
            row.title_overrides = payload_titles
            row.subtasks_flat = payload_flat
            row.hide_subtasks = payload_hide
    else:
        row.column_order = payload_order
        row.hidden_status_keys = payload_hidden
        row.title_overrides = payload_titles
        row.subtasks_flat = payload_flat
        row.hide_subtasks = payload_hide

    await session.commit()
    await session.refresh(row)
    return _row_to_read(row)
