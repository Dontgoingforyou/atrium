"""Тесты модели PortalSpecialistProfile."""

from __future__ import annotations

from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


def _user_profile(**kwargs: object) -> PortalUserProfile:
    base: dict[str, object] = {
        "sub": "spec-sub",
        "email": None,
        "full_name": None,
        "username": None,
    }
    base.update(kwargs)
    return PortalUserProfile(**base)  # type: ignore[arg-type]


def test_str_uses_full_name_from_user_profile() -> None:
    profile = PortalSpecialistProfile(specialist_sub="spec-sub")
    profile.__dict__["user_profile"] = _user_profile(full_name="Иван Иванов", email="i@example.com")
    assert str(profile) == "Иван Иванов"


def test_str_falls_back_to_email_or_username() -> None:
    by_email = PortalSpecialistProfile(specialist_sub="a")
    by_email.__dict__["user_profile"] = _user_profile(sub="a", email="mail@example.com")

    by_username = PortalSpecialistProfile(specialist_sub="b")
    by_username.__dict__["user_profile"] = _user_profile(sub="b", username="user_b")

    assert str(by_email) == "mail@example.com"
    assert str(by_username) == "user_b"


def test_str_without_display_name_uses_short_sub() -> None:
    profile = PortalSpecialistProfile(specialist_sub="short-sub")
    profile.__dict__["user_profile"] = _user_profile(sub="short-sub")
    assert str(profile) == "short-sub"


def test_str_without_user_profile_truncates_long_sub() -> None:
    long_sub = "x" * 25
    profile = PortalSpecialistProfile(specialist_sub=long_sub)
    assert str(profile) == long_sub[:20] + "…"
