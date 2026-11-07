from __future__ import annotations

from app.core.permissions import is_timesheet_only
from app.schemas.auth import UserPublic


def user_can_access_documents(user: UserPublic) -> bool:
    """Проверить доступ пользователя к документам портала.

    Администраторы портала имеют доступ всегда.
    Пользователи с ограничением «только таймшиты» (должность или группа students) — deny.
    Все остальные авторизованные пользователи видят документы.
    """
    if user.is_portal_admin:
        return True
    return not is_timesheet_only(user)


def user_can_access_developer_docs(user: UserPublic) -> bool:
    """Доступ к разделу «Документы для разработчиков».

    Полный доступ к документам — да; режим «только таймшиты» (АУ и студенты) —
    точечное исключение: видят только этот раздел.
    """
    if user_can_access_documents(user):
        return True
    return is_timesheet_only(user)
