"""Контракт предикатов документов: матрица ролей, не HTTP и не deps_rbac."""

from __future__ import annotations

from collections.abc import Callable

import pytest
from app.core.auth_constants import IDP_GROUP_DEVELOPER
from app.schemas.auth import UserPublic
from app.services.rbac import (
    user_can_access_developer_docs,
    user_can_access_documents,
)

from tests.helpers.portal_test_users import (
    user_au_specialist_with_outstaff,
    user_manager_students_outstaff,
    user_outstaff_not_manager,
    user_portal_admin,
    user_portal_developer,
    user_portal_manager,
    user_portal_no_idp_groups,
    user_portal_regular,
)


def _students_without_position() -> UserPublic:
    """Группа students без claim position — timesheet-only по IdP."""
    return UserPublic(
        sub="students-no-pos",
        email="students.nopos@example.com",
        username="students.nopos",
        full_name="Students No Position",
        idp_groups=[IDP_GROUP_DEVELOPER],
        is_portal_admin=False,
        position=None,
    )


@pytest.mark.parametrize(
    ("user_factory", "can_documents"),
    [
        (user_portal_admin, True),
        (user_portal_regular, True),
        (user_portal_manager, True),
        (user_portal_no_idp_groups, True),
        (user_outstaff_not_manager, True),
        (user_manager_students_outstaff, True),
        (user_portal_developer, False),
        (user_au_specialist_with_outstaff, False),
        (_students_without_position, False),
    ],
    ids=[
        "admin",
        "regular",
        "manager",
        "no_idp",
        "outstaff_no_gid",
        "au_chief",
        "developer",
        "au_specialist",
        "students_no_position",
    ],
)
def test_document_access_predicates(
    user_factory: Callable[[], UserPublic],
    can_documents: bool,
) -> None:
    user = user_factory()
    assert user_can_access_documents(user) is can_documents
    assert user_can_access_developer_docs(user) is True
