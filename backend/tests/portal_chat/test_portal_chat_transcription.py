"""Тесты транскрибации голосовых вложений через OpenAI Whisper.

Покрытие (testing.mdc): успех, переиспользование готового транскрипта (без повторного
вызова внешнего API), валидация (не голосовое сообщение), недоступность сервиса
(нет ключа / ошибка OpenAI), 403 для не-участника чата — внешний API всегда мокается.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from app.api.deps import get_db_session
from app.api.deps_auth import get_current_user
from app.core.config import Settings
from app.core.exceptions import ForbiddenError, ServiceUnavailableError, ValidationError
from app.main import app
from app.portal_chat.services import chat as chat_svc
from app.portal_chat.services import transcription as transcription_svc
from httpx import ASGITransport, AsyncClient
from openai import OpenAIError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import make_oidc_settings
from tests.helpers.portal_test_users import user_portal_admin, user_portal_regular, user_portal_user_b

_WEBM_MAGIC = b"\x1a\x45\xdf\xa3" + b"\x00" * 12


async def _make_voice_attachment(
    session: AsyncSession,
    *,
    chat_id: uuid.UUID,
    uploader_sub: str,
    voice_transcript: str | None = None,
) -> object:
    from app.infrastructure.db.models.portal_chat import PortalChatAttachment

    att = PortalChatAttachment(
        chat_id=chat_id,
        uploader_sub=uploader_sub,
        original_filename="voice.webm",
        content_type="audio/webm",
        file_size=10,
        storage_key="voice-key",
        voice_duration_seconds=3.5,
        voice_transcript=voice_transcript,
    )
    session.add(att)
    await session.commit()
    await session.refresh(att)
    return att


@pytest.fixture(autouse=True)
def _reset_client_singleton() -> object:
    """Сбрасывает модульный singleton AsyncOpenAI между тестами."""
    transcription_svc._client = None
    yield
    transcription_svc._client = None


async def test_transcribe_voice_attachment_success(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = await _make_voice_attachment(sqlite_session, chat_id=chat.id, uploader_sub=admin.sub)

    fake_client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(text="  привет мир  ")))
        )
    )
    monkeypatch.setattr(transcription_svc, "_client_singleton", lambda: fake_client)
    monkeypatch.setattr(
        transcription_svc,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_base_url="",
            openai_whisper_model="whisper-1",
            chat_whisper_max_size_bytes=26_214_400,
        ),
    )

    with patch.object(transcription_svc, "async_download_object_bytes", new_callable=AsyncMock) as dl:
        dl.return_value = _WEBM_MAGIC
        result = await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)

    assert result.voice_transcript == "привет мир"
    dl.assert_awaited_once_with(att.storage_key)
    fake_client.audio.transcriptions.create.assert_awaited_once()


async def test_transcribe_voice_attachment_reuses_existing_transcript(
    sqlite_session: AsyncSession,
) -> None:
    """Если транскрипт уже есть — внешний API не вызывается повторно."""
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = await _make_voice_attachment(
        sqlite_session, chat_id=chat.id, uploader_sub=admin.sub, voice_transcript="уже есть"
    )

    with patch.object(transcription_svc, "async_download_object_bytes", new_callable=AsyncMock) as dl:
        result = await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)

    assert result.voice_transcript == "уже есть"
    dl.assert_not_called()


async def test_transcribe_non_voice_attachment_validation(
    sqlite_session: AsyncSession,
) -> None:
    """Вложение без voice_duration_seconds — ValidationError."""
    from app.infrastructure.db.models.portal_chat import PortalChatAttachment

    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="doc.pdf",
        content_type="application/pdf",
        file_size=10,
        storage_key="doc-key",
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    await sqlite_session.refresh(att)

    with pytest.raises(ValidationError, match="только для голосовых"):
        await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)


async def test_transcribe_rejects_duration_spoof_on_non_audio(
    sqlite_session: AsyncSession,
) -> None:
    """voice_duration_seconds на PDF не делает вложение голосовым."""
    from app.infrastructure.db.models.portal_chat import PortalChatAttachment

    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = PortalChatAttachment(
        chat_id=chat.id,
        uploader_sub=admin.sub,
        original_filename="doc.pdf",
        content_type="application/pdf",
        file_size=10,
        storage_key="doc-key",
        voice_duration_seconds=1.0,
    )
    sqlite_session.add(att)
    await sqlite_session.commit()
    await sqlite_session.refresh(att)

    with pytest.raises(ValidationError, match="только для голосовых"):
        await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)


async def test_transcribe_rejects_oversized_audio(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = await _make_voice_attachment(sqlite_session, chat_id=chat.id, uploader_sub=admin.sub)
    att.file_size = 30_000_000
    await sqlite_session.commit()

    monkeypatch.setattr(
        transcription_svc,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_base_url="",
            openai_whisper_model="whisper-1",
            chat_whisper_max_size_bytes=1024,
        ),
    )
    with pytest.raises(ValidationError, match="слишком большое"):
        await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)


async def test_transcribe_missing_api_key_service_unavailable(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = await _make_voice_attachment(sqlite_session, chat_id=chat.id, uploader_sub=admin.sub)

    fake_settings = SimpleNamespace(
        openai_api_key="",
        openai_base_url="",
        openai_whisper_model="whisper-1",
        chat_whisper_max_size_bytes=26_214_400,
    )
    monkeypatch.setattr(transcription_svc, "get_settings", lambda: fake_settings)

    with patch.object(transcription_svc, "async_download_object_bytes", new_callable=AsyncMock) as dl:
        with pytest.raises(ServiceUnavailableError, match="OPENAI_API_KEY"):
            await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)
        dl.assert_not_called()


async def test_transcribe_openai_error_raises_service_unavailable(
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = await _make_voice_attachment(sqlite_session, chat_id=chat.id, uploader_sub=admin.sub)

    fake_client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(
                create=AsyncMock(side_effect=OpenAIError("boom")),
            )
        )
    )
    monkeypatch.setattr(transcription_svc, "_client_singleton", lambda: fake_client)
    monkeypatch.setattr(
        transcription_svc,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_base_url="",
            openai_whisper_model="whisper-1",
            chat_whisper_max_size_bytes=26_214_400,
        ),
    )

    with patch.object(
        transcription_svc, "async_download_object_bytes", new_callable=AsyncMock, return_value=_WEBM_MAGIC
    ):
        with pytest.raises(ServiceUnavailableError, match="Не удалось транскрибировать"):
            await transcription_svc.transcribe_voice_attachment(sqlite_session, admin, chat.id, att.id)


async def test_transcribe_voice_attachment_non_member_forbidden(
    sqlite_session: AsyncSession,
) -> None:
    admin = user_portal_admin()
    other = user_portal_regular()
    user_b = user_portal_user_b()
    chat = await chat_svc.get_or_create_direct_chat(sqlite_session, admin, other.sub)
    att = await _make_voice_attachment(sqlite_session, chat_id=chat.id, uploader_sub=admin.sub)

    with pytest.raises(ForbiddenError):
        await transcription_svc.transcribe_voice_attachment(sqlite_session, user_b, chat.id, att.id)


# ---------------------------------------------------------------------------
# HTTP-уровень: POST /portal/chats/{id}/attachments/{aid}/transcribe
# ---------------------------------------------------------------------------


async def test_transcribe_route_success(
    client_admin: AsyncClient,
    sqlite_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    r_chat = await client_admin.post(
        "/api/v1/portal/chats",
        json={"title": "Чат с ГС", "member_subs": [user_portal_regular().sub]},
    )
    chat_id = r_chat.json()["id"]
    att = await _make_voice_attachment(sqlite_session, chat_id=uuid.UUID(chat_id), uploader_sub=user_portal_admin().sub)

    fake_client = SimpleNamespace(
        audio=SimpleNamespace(
            transcriptions=SimpleNamespace(create=AsyncMock(return_value=SimpleNamespace(text="текст записи")))
        )
    )
    monkeypatch.setattr(transcription_svc, "_client_singleton", lambda: fake_client)
    monkeypatch.setattr(
        transcription_svc,
        "get_settings",
        lambda: SimpleNamespace(
            openai_api_key="sk-test",
            openai_base_url="",
            openai_whisper_model="whisper-1",
            chat_whisper_max_size_bytes=26_214_400,
        ),
    )

    with (
        patch.object(
            transcription_svc, "async_download_object_bytes", new_callable=AsyncMock, return_value=_WEBM_MAGIC
        ),
        patch("app.portal_chat.routes.messages.att_svc.build_download_url", return_value="https://dl.example/x"),
    ):
        r = await client_admin.post(f"/api/v1/portal/chats/{chat_id}/attachments/{att.id}/transcribe")

    assert r.status_code == 200, r.text
    assert r.json()["transcript"] == "текст записи"


async def test_transcribe_route_403_non_member(
    sqlite_session: AsyncSession,
    patch_oidc_settings: Settings,
) -> None:
    async def _db() -> AsyncIterator[AsyncSession]:
        yield sqlite_session

    transport = ASGITransport(app=app)

    app.dependency_overrides[get_db_session] = _db
    app.dependency_overrides[get_current_user] = user_portal_admin
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r_chat = await ac.post(
            "/api/v1/portal/chats",
            json={"title": "Закрытый", "member_subs": [user_portal_regular().sub]},
        )
        chat_id = r_chat.json()["id"]
    att = await _make_voice_attachment(sqlite_session, chat_id=uuid.UUID(chat_id), uploader_sub=user_portal_admin().sub)

    app.dependency_overrides[get_current_user] = user_portal_user_b
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.post(f"/api/v1/portal/chats/{chat_id}/attachments/{att.id}/transcribe")
    from tests.portal_chat.conftest import assert_api_error

    assert_api_error(r, 403, "forbidden")

    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db_session, None)


def test_whisper_client_uses_shared_key_and_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whisper и эмбеддинги читают один OPENAI_API_KEY и один OPENAI_BASE_URL."""
    transcription_svc._client = None
    s = make_oidc_settings(
        openai_api_key="sk-shared",
        openai_base_url="https://llmapi.example/api/v1",
        openai_whisper_timeout_seconds=60.0,
    )
    monkeypatch.setattr(transcription_svc, "get_settings", lambda: s)
    try:
        with patch("app.services.openai_client.AsyncOpenAI") as client_cls:
            transcription_svc._get_client()
        assert client_cls.call_args.kwargs["api_key"] == "sk-shared"
        assert client_cls.call_args.kwargs["base_url"] == "https://llmapi.example/api/v1"
        assert client_cls.call_args.kwargs["timeout"] == 60.0
    finally:
        transcription_svc._client = None


def test_whisper_client_uses_dedicated_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Whisper берёт openai_whisper_timeout_seconds, не общий http_client_timeout."""
    transcription_svc._client = None
    s = make_oidc_settings(
        openai_api_key="sk-test",
        openai_whisper_timeout_seconds=60.0,
        http_client_timeout_seconds=20.0,
    )
    monkeypatch.setattr(transcription_svc, "get_settings", lambda: s)
    try:
        with patch("app.services.openai_client.AsyncOpenAI") as AO:
            transcription_svc._get_client()
        assert AO.call_args.kwargs["timeout"] == 60.0
    finally:
        transcription_svc._client = None
