"""Интеграция Effective Admin (фото сотрудников и сверка почт)."""

from app.integrations.effective_admin.client import EffectiveAdminPhotoClient, PhotoBytes, PhotoMeta
from app.integrations.effective_admin.emails_check import EffectiveAdminEmailsClient, EmailsCheckResult
from app.integrations.effective_admin.username import username_from_email

__all__ = [
    "EffectiveAdminEmailsClient",
    "EffectiveAdminPhotoClient",
    "EmailsCheckResult",
    "PhotoBytes",
    "PhotoMeta",
    "username_from_email",
]
