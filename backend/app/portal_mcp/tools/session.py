"""Кто вызывает MCP и жив ли процесс API."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from app.portal_mcp.auth import clamp_limit, dump_dict, mcp_call
from app.portal_mcp.constants import LIST_LIMIT_DEFAULT


def register(mcp: FastMCP) -> None:
    @mcp.tool(description="Кто вызывает MCP: sub, признак админа и отдел.")
    async def whoami() -> dict[str, object]:
        async with mcp_call("whoami") as call:
            return {
                "sub": call.user.sub,
                "email": call.user.email,
                "full_name": call.user.full_name,
                "is_portal_admin": call.user.is_portal_admin,
                "gid_number": call.user.gid_number,
            }

    @mcp.tool(
        description=(
            "Сотрудники портала для выбора исполнителя: sub, имя и почта. Чужое имя брать отсюда, sub не выдумывать."
        ),
    )
    async def portal_users_list(
        limit: int = LIST_LIMIT_DEFAULT,
        skip: int = 0,
    ) -> list[dict[str, object]]:
        from app.services.portal_user import list_portal_users

        async with mcp_call("portal_users_list") as call:
            users, _total = await list_portal_users(
                call.session,
                skip=skip,
                limit=clamp_limit(limit),
                http=call.http,
            )
            return [{"sub": user.sub, "display_name": user.display_name, "email": user.email} for user in users]

    @mcp.tool(description="Процесс API отвечает. Это не проверка базы и не чужих сервисов.")
    async def api_health() -> dict[str, str]:
        async with mcp_call("api_health"):
            return {"status": "ok"}

    @mcp.tool(description="Сводка главной: свои задачи и избранное. Блок команды есть только у админа.")
    async def home_summary(assignee_sub: str | None = None) -> dict[str, object]:
        from app.portal_home.services.home import build_portal_home

        async with mcp_call("home_summary") as call:
            home = await build_portal_home(call.session, call.user, assignee_sub=assignee_sub)
            return dump_dict(home)
