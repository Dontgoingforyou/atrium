"""HTTP-ветки ProfileDirectoryPhotoClient."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from urllib.parse import quote

import httpx
import pytest
from app.core.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from app.integrations.profile_directory.client import ProfileDirectoryPhotoClient
from app.services.avatar_upload_common import AVATAR_MAX_BYTES
from tests.conftest import make_oidc_settings

_JPEG = b"\xff\xd8\xff" + b"\x00" * 32


class _StreamCM:
    def __init__(self, response: MagicMock) -> None:
        self._response = response

    async def __aenter__(self) -> MagicMock:
        return self._response

    async def __aexit__(self, *args: object) -> bool:
        return False


def _settings(**kwargs: Any) -> Any:
    data: dict[str, Any] = {"profile_directory_base_url": "https://ea.example"}
    data.update(kwargs)
    return make_oidc_settings(**data)


def _photo_response(
    *,
    status_code: int = 200,
    content_type: str = "image/jpeg",
    body: bytes = _JPEG,
    content_length: str | None = None,
) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    headers: dict[str, str] = {"content-type": content_type}
    if content_length is not None:
        headers["content-length"] = content_length
    response.headers = headers

    async def _aiter() -> Any:
        yield body

    response.aiter_bytes = _aiter
    return response


@pytest.fixture
def http() -> MagicMock:
    mock = MagicMock(spec=httpx.AsyncClient)
    mock.get = AsyncMock()
    mock.post = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(http: MagicMock) -> ProfileDirectoryPhotoClient:
    return ProfileDirectoryPhotoClient(_settings(), http)


@pytest.mark.anyio
async def test_get_user_photo_disabled_raises(http: MagicMock) -> None:
    disabled = ProfileDirectoryPhotoClient(_settings(profile_directory_base_url=""), http)
    with pytest.raises(ServiceUnavailableError, match="не настроена"):
        await disabled.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_quotes_username_and_accepts_jpeg(
    client: ProfileDirectoryPhotoClient,
    http: MagicMock,
) -> None:
    http.stream.return_value = _StreamCM(_photo_response())
    photo = await client.get_user_photo(username="иван/x", bearer_token="tok")
    assert photo.content_type == "image/jpeg"
    assert photo.content.startswith(b"\xff\xd8\xff")
    url = http.stream.call_args.args[1]
    assert quote("иван/x", safe="") in url
    assert url.endswith(f"/api/v1/users/{quote('иван/x', safe='')}/photo")


@pytest.mark.anyio
async def test_get_user_photo_accepts_image_jpg_alias(
    client: ProfileDirectoryPhotoClient,
    http: MagicMock,
) -> None:
    http.stream.return_value = _StreamCM(_photo_response(content_type="image/jpg"))
    photo = await client.get_user_photo(username="ivan", bearer_token="tok")
    assert photo.content_type == "image/jpeg"


@pytest.mark.anyio
async def test_get_user_photo_accepts_content_type_with_charset(
    client: ProfileDirectoryPhotoClient,
    http: MagicMock,
) -> None:
    http.stream.return_value = _StreamCM(_photo_response(content_type="image/jpeg; charset=binary"))
    photo = await client.get_user_photo(username="ivan", bearer_token="tok")
    assert photo.content_type == "image/jpeg"


@pytest.mark.anyio
async def test_get_user_photo_ignores_invalid_content_length(
    client: ProfileDirectoryPhotoClient,
    http: MagicMock,
) -> None:
    http.stream.return_value = _StreamCM(_photo_response(content_length="not-a-number"))
    photo = await client.get_user_photo(username="ivan", bearer_token="tok")
    assert photo.content.startswith(b"\xff\xd8\xff")


@pytest.mark.anyio
async def test_get_user_photo_rejects_html(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.stream.return_value = _StreamCM(_photo_response(content_type="text/html", body=b"<html>"))
    with pytest.raises(ServiceUnavailableError, match="недопустимый тип"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_rejects_magic_mismatch(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.stream.return_value = _StreamCM(_photo_response(body=b"not-a-jpeg"))
    with pytest.raises(ServiceUnavailableError, match="недопустимый тип"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_rejects_oversized_content_length(
    client: ProfileDirectoryPhotoClient,
    http: MagicMock,
) -> None:
    http.stream.return_value = _StreamCM(
        _photo_response(content_length=str(AVATAR_MAX_BYTES + 1)),
    )
    with pytest.raises(ServiceUnavailableError, match="большой"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_rejects_oversized_stream_without_content_length(
    client: ProfileDirectoryPhotoClient,
    http: MagicMock,
) -> None:
    http.stream.return_value = _StreamCM(_photo_response(body=b"\xff\xd8\xff" + b"\x00" * AVATAR_MAX_BYTES))
    with pytest.raises(ServiceUnavailableError, match="большой"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_404_raises_not_found(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.stream.return_value = _StreamCM(_photo_response(status_code=404))
    with pytest.raises(NotFoundError, match="не найдено"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_http_500_raises(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.stream.return_value = _StreamCM(_photo_response(status_code=500))
    with pytest.raises(ServiceUnavailableError, match="вернул ошибку"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_user_photo_network_error(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.stream.side_effect = httpx.ConnectError("refused")
    with pytest.raises(ServiceUnavailableError, match="временно недоступен"):
        await client.get_user_photo(username="ivan", bearer_token="tok")


@pytest.mark.anyio
async def test_get_me_photo_meta_success(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"has_photo": True, "version": 7}
    http.get = AsyncMock(return_value=response)
    meta = await client.get_me_photo_meta(bearer_token="tok")
    assert meta.has_photo is True
    assert meta.version == 7
    http.get.assert_awaited_once()
    assert http.get.await_args.args[0].endswith("/api/v1/me/photo/meta")


@pytest.mark.anyio
async def test_get_me_photo_meta_non_int_version(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"has_photo": 1, "version": "3"}
    http.get = AsyncMock(return_value=response)
    meta = await client.get_me_photo_meta(bearer_token="tok")
    assert meta.has_photo is True
    assert meta.version is None


@pytest.mark.anyio
async def test_get_me_photo_meta_non_dict_json(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = [{"has_photo": True}]
    http.get = AsyncMock(return_value=response)
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.get_me_photo_meta(bearer_token="tok")


@pytest.mark.anyio
async def test_get_me_photo_meta_invalid_json(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 200
    response.json.side_effect = ValueError("nope")
    http.get = AsyncMock(return_value=response)
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.get_me_photo_meta(bearer_token="tok")


@pytest.mark.anyio
async def test_get_me_photo_meta_http_500(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 500
    http.get = AsyncMock(return_value=response)
    with pytest.raises(ServiceUnavailableError, match="ошибку"):
        await client.get_me_photo_meta(bearer_token="tok")


@pytest.mark.anyio
async def test_get_me_photo_meta_network_error(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ServiceUnavailableError, match="временно недоступен"):
        await client.get_me_photo_meta(bearer_token="tok")


@pytest.mark.anyio
async def test_upload_my_photo_sends_em_client_header(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 204
    http.post = AsyncMock(return_value=response)
    await client.upload_my_photo(
        bearer_token="tok",
        file_name="a.jpg",
        content=_JPEG,
        content_type="image/jpeg",
    )
    headers = http.post.await_args.kwargs["headers"]
    assert headers["X-Client"] == "portal"
    assert headers["Authorization"] == "Bearer tok"


@pytest.mark.anyio
async def test_upload_my_photo_422_raises_validation(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 422
    http.post = AsyncMock(return_value=response)
    with pytest.raises(ValidationError, match="отклонён"):
        await client.upload_my_photo(
            bearer_token="tok",
            file_name="a.jpg",
            content=_JPEG,
            content_type="image/jpeg",
        )


@pytest.mark.anyio
async def test_upload_my_photo_http_500(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 500
    http.post = AsyncMock(return_value=response)
    with pytest.raises(ServiceUnavailableError, match="загрузке"):
        await client.upload_my_photo(
            bearer_token="tok",
            file_name="a.jpg",
            content=_JPEG,
            content_type="image/jpeg",
        )


@pytest.mark.anyio
async def test_upload_my_photo_network_error(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.post = AsyncMock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ServiceUnavailableError, match="временно недоступен"):
        await client.upload_my_photo(
            bearer_token="tok",
            file_name="a.jpg",
            content=_JPEG,
            content_type="image/jpeg",
        )


@pytest.mark.anyio
async def test_delete_my_photo_404_is_ok(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 404
    http.delete = AsyncMock(return_value=response)
    await client.delete_my_photo(bearer_token="tok")


@pytest.mark.anyio
async def test_delete_my_photo_http_500(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    response = MagicMock()
    response.status_code = 500
    http.delete = AsyncMock(return_value=response)
    with pytest.raises(ServiceUnavailableError, match="удалении"):
        await client.delete_my_photo(bearer_token="tok")


@pytest.mark.anyio
async def test_delete_my_photo_network_error(client: ProfileDirectoryPhotoClient, http: MagicMock) -> None:
    http.delete = AsyncMock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(ServiceUnavailableError, match="временно недоступен"):
        await client.delete_my_photo(bearer_token="tok")
