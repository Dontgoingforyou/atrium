"""Утилиты превью для Telegram."""

from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.portal_telegram.services.telegram_text_preview import (
    TG_BODY_PREVIEW_MAX,
    attachment_preview_label,
    plain_text_from_html,
    profile_display,
    snippet,
    split_leading_portal_mention,
    strip_isolated_at_signs,
    telegram_plain_preview,
)


def test_split_leading_mention_longest_label_wins() -> None:
    labels = ["Mira Holt", "Mira"]
    body = "@Mira Holt привет"
    who, rest = split_leading_portal_mention(body, labels)
    assert who == "Mira Holt"
    assert rest == "привет"


def test_split_leading_mention_no_match() -> None:
    who, rest = split_leading_portal_mention("@Other х", ["Mira"])
    assert who is None
    assert rest == "@Other х"


def test_strip_isolated_at_preserves_email() -> None:
    assert strip_isolated_at_signs("см. a@b.co и @User") == "см. a@b.co и User"


def test_profile_display_prefers_full_name() -> None:
    p = PortalUserProfile(sub="s", email="e@x", username="u", full_name="Имя Полное")
    assert profile_display(p) == "Имя Полное"


def test_profile_display_email_when_no_full_name() -> None:
    p = PortalUserProfile(sub="s", email="mail@x", username="u", full_name=None)
    assert profile_display(p) == "mail@x"


def test_profile_display_username_when_no_email() -> None:
    p = PortalUserProfile(sub="s", email=None, username="nick", full_name=None)
    assert profile_display(p) == "nick"


def test_profile_display_sub_when_only_sub() -> None:
    p = PortalUserProfile(sub="only-sub", email=None, username=None, full_name=None)
    assert profile_display(p) == "only-sub"


def test_profile_display_fallback_when_profile_empty() -> None:
    p = PortalUserProfile(sub=" ", email=None, username=None, full_name="  ")
    assert profile_display(p, fallback_sub="fb") == "fb"


def test_profile_display_none_uses_fallback() -> None:
    assert profile_display(None, fallback_sub="  sub  ") == "sub"


def test_snippet_collapses_whitespace() -> None:
    assert snippet("  a \n\t b  ") == "a b"


def test_snippet_under_limit_unchanged() -> None:
    assert snippet("коротко") == "коротко"


def test_snippet_truncates_with_ellipsis() -> None:
    long = "x" * (TG_BODY_PREVIEW_MAX + 10)
    out = snippet(long)
    assert len(out) <= TG_BODY_PREVIEW_MAX + 1
    assert out.endswith("…")


def test_plain_text_from_html_strips_tags_and_entities() -> None:
    assert plain_text_from_html("<p>a&nbsp;b</p>") == "a b"
    assert plain_text_from_html("x&lt;y") == "x<y"


def test_plain_text_from_html_strips_script_and_style() -> None:
    raw = '<script>alert(1)</script><p>ok</p><span style="color:red">x</span>'
    out = plain_text_from_html(raw)
    assert "<script>" not in out
    assert "style=" not in out
    assert "ok" in out
    assert "x" in out


def test_telegram_plain_preview_fullwidth_at_for_no_auto_link() -> None:
    assert "@" not in telegram_plain_preview("@Иван Петров привет")
    assert "\uff20Иван" in telegram_plain_preview("@Иван Петров привет")


def test_attachment_preview_label_zero() -> None:
    assert attachment_preview_label(0) == ""


def test_attachment_preview_label_one() -> None:
    assert attachment_preview_label(1) == "Вложение"


def test_attachment_preview_label_two_to_four() -> None:
    assert attachment_preview_label(2) == "2 вложения"
    assert attachment_preview_label(4) == "4 вложения"


def test_attachment_preview_label_many() -> None:
    assert attachment_preview_label(5) == "5 вложений"


def test_split_leading_mention_empty_body() -> None:
    who, rest = split_leading_portal_mention("", ["A"])
    assert who is None
    assert rest == ""


def test_split_leading_mention_skips_blank_labels() -> None:
    who, rest = split_leading_portal_mention("@Real текст", ["", "  ", "Real"])
    assert who == "Real"
    assert rest == "текст"
