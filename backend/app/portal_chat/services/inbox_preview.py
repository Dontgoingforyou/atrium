from __future__ import annotations

_INBOX_PREVIEW_MAX_LEN = 160


def build_inbox_preview_text(*, body: str, attachment_content_types: list[str]) -> str:
    """Формирует усечённый текст или подпись по вложениям (без персональных данных из имён файлов)."""
    text = (body or "").strip()
    if text:
        if len(text) <= _INBOX_PREVIEW_MAX_LEN:
            return text
        return text[: _INBOX_PREVIEW_MAX_LEN - 1] + "…"
    if not attachment_content_types:
        return "Новое сообщение"
    n = len(attachment_content_types)
    all_audio = all(ct.lower().startswith("audio/") for ct in attachment_content_types)
    if all_audio:
        return "Голосовое сообщение" if n == 1 else "Голосовые сообщения"
    all_image = all(ct.lower().startswith("image/") for ct in attachment_content_types)
    if all_image:
        return "Изображение" if n == 1 else "Изображения"
    return "Вложение" if n == 1 else "Вложения"
