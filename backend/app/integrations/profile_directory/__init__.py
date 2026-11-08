"""Интеграция сервиса профилей (фото сотрудников и сверка почт)."""

from app.integrations.profile_directory.client import ProfileDirectoryPhotoClient, PhotoBytes, PhotoMeta
from app.integrations.profile_directory.emails_check import ProfileDirectoryEmailsClient, EmailsCheckResult
from app.integrations.profile_directory.username import username_from_email

__all__ = [
    "ProfileDirectoryEmailsClient",
    "ProfileDirectoryPhotoClient",
    "EmailsCheckResult",
    "PhotoBytes",
    "PhotoMeta",
    "username_from_email",
]
