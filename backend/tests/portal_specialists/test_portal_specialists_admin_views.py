"""Юнит-тесты SQLAdmin-вьюх и форматтеров portal_specialists."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from markupsafe import Markup
from sqlalchemy.ext.asyncio import AsyncSession


def test_profile_display_none_returns_dash() -> None:
    from app.portal_specialists.admin.board import profile_display as _profile_display

    assert _profile_display(None, "short") == "—"
    assert _profile_display(None, "a" * 20) == "—"


def test_profile_display_with_profile_variants() -> None:
    from app.portal_specialists.admin.board import profile_display as _profile_display

    both = SimpleNamespace(full_name="Иван", email="i@example.com")
    assert _profile_display(both, "fallback") == "Иван (i@example.com)"

    name_only = SimpleNamespace(full_name="Пётр", email="")
    assert _profile_display(name_only, "sub-fallback") == "Пётр"

    email_only = SimpleNamespace(full_name="", email="e@mail.test")
    assert _profile_display(email_only, "sub-fallback") == "e@mail.test"

    empty = SimpleNamespace(full_name="", email="")
    assert _profile_display(empty, "onlysub") == "—"


def test_fmt_manager_and_specialist_delegate_to_profile_display() -> None:
    from app.portal_specialists.admin.board import _fmt_manager, _fmt_specialist

    prof = SimpleNamespace(full_name="М", email="m@x.test")
    row_mgr = SimpleNamespace(manager_profile=prof, manager_sub="mgr-sub")
    assert _fmt_manager(row_mgr, "manager_profile") == "М (m@x.test)"
    row_spec = SimpleNamespace(specialist_profile=None, specialist_sub="spec-only")
    assert _fmt_specialist(row_spec, "specialist_profile") == "—"


def test_fmt_status_none_colored_and_escaped() -> None:
    from app.portal_specialists.admin.board import _fmt_status

    assert str(_fmt_status(SimpleNamespace(status=None), "status")) == "—"

    st = SimpleNamespace(color='#f00"><script>x</script>', title="<b>Title</b>")
    out = _fmt_status(SimpleNamespace(status=st), "status")
    assert isinstance(out, Markup)
    s = str(out)
    assert "<script>" not in s
    assert "&lt;script&gt;" in s
    assert "&lt;b&gt;Title&lt;/b&gt;" in s
    assert "●" in s


def test_telegram_admin_markup_escapes_unsafe_href() -> None:
    from app.portal_specialists.admin.profile import _telegram_admin_markup

    out = _telegram_admin_markup('"><script>alert(1)</script>')
    s = str(out)
    assert "<script>" not in s
    assert "&quot;" in s or "&lt;" in s


def _compile_profile_search(term: str) -> str:
    from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
    from app.portal_specialists.admin.profile import PortalSpecialistProfileAdmin
    from sqlalchemy import select

    admin = PortalSpecialistProfileAdmin()
    stmt = admin.search_query(select(PortalSpecialistProfile), term)
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
    return str(compiled).lower()


def test_profile_admin_search_query_matches_name_and_email() -> None:
    sql_darya = _compile_profile_search("darya")
    assert "full_name" in sql_darya
    assert "email" in sql_darya
    assert "darya" in sql_darya
    assert "location" in sql_darya
    assert "telegram" in sql_darya

    sql_fio = _compile_profile_search("User Search")
    assert "full_name" in sql_fio
    assert "kseniya voroshkina" in sql_fio


def test_profile_admin_search_on_list_query_compiles() -> None:
    """SQLAdmin вызывает search_query(list_query()) — JOIN + EXISTS не должны ломать FROM."""
    from types import SimpleNamespace

    from app.portal_specialists.admin.profile import PortalSpecialistProfileAdmin

    admin = PortalSpecialistProfileAdmin()
    stmt = admin.search_query(admin.list_query(SimpleNamespace()), "darya")
    compiled = stmt.compile(compile_kwargs={"literal_binds": True})
    sql = str(compiled).lower()
    assert "darya" in sql
    assert "exists" in sql


def test_profile_admin_search_query_escapes_ilike_wildcards() -> None:
    sql = _compile_profile_search("%_")
    assert "escape" in sql
    assert r"\%" in sql or r"\\%" in sql
    assert r"\_" in sql or r"\\_" in sql


def test_profile_admin_search_placeholder_lists_name_and_email() -> None:
    from app.portal_specialists.admin.profile import PortalSpecialistProfileAdmin

    placeholder = PortalSpecialistProfileAdmin().search_placeholder()
    assert "ФИО" in placeholder
    assert "Email" in placeholder
    assert "Локация" in placeholder
    assert "Telegram" in placeholder


def test_profile_admin_cannot_delete() -> None:
    from app.portal_specialists.admin.profile import PortalSpecialistProfileAdmin

    assert PortalSpecialistProfileAdmin().can_delete is False


@pytest.mark.asyncio
async def test_profile_admin_list_hides_denylist_and_other_dept(sqlite_session: AsyncSession) -> None:
    from types import SimpleNamespace

    from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
    from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
    from app.portal_specialists.admin.profile import PortalSpecialistProfileAdmin

    sqlite_session.add(PortalUserProfile(sub="au-ok", email="ok@em.test", full_name="Ok", gid_number="10000"))
    sqlite_session.add(
        PortalUserProfile(
            sub="fired",
            email="hidden.two@example.com",
            full_name="User Search",
            gid_number="10000",
        )
    )
    sqlite_session.add(PortalUserProfile(sub="other", email="ceo@em.test", full_name="Other", gid_number="20000"))
    await sqlite_session.flush()
    sqlite_session.add(PortalSpecialistProfile(specialist_sub="au-ok"))
    sqlite_session.add(PortalSpecialistProfile(specialist_sub="fired"))
    sqlite_session.add(PortalSpecialistProfile(specialist_sub="other"))
    await sqlite_session.commit()

    admin = PortalSpecialistProfileAdmin()
    stmt = admin.list_query(SimpleNamespace())
    rows = (await sqlite_session.execute(stmt)).scalars().unique().all()
    subs = {row.specialist_sub for row in rows}
    assert "au-ok" in subs
    assert "fired" not in subs
    assert "other" not in subs

    searched = admin.search_query(admin.list_query(SimpleNamespace()), "ok")
    found = (await sqlite_session.execute(searched)).scalars().unique().all()
    assert {row.specialist_sub for row in found} == {"au-ok"}
