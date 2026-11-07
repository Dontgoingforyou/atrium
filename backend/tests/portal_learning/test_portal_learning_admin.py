"""Контракт SQLAdmin обучения: хук автора и флаги can_*."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from app.portal_learning.admin.checklist import PortalUserChecklistAdmin
from app.portal_learning.admin.material import PortalLearningMaterialAdmin
from app.portal_learning.admin.quiz import PortalQuizAttemptAdmin


@pytest.mark.asyncio
async def test_material_admin_on_model_change_sets_created_by_sub() -> None:
    admin = PortalLearningMaterialAdmin()
    model = MagicMock()
    model.created_by_sub = "old-sub"
    model.created_by_profile = SimpleNamespace(sub="from-profile")
    await admin.on_model_change({}, model, True, MagicMock())
    assert model.created_by_sub == "from-profile"


def test_progress_and_attempt_admin_are_read_only_except_delete() -> None:
    assert PortalUserChecklistAdmin.can_create is False
    assert PortalUserChecklistAdmin.can_edit is False
    assert PortalUserChecklistAdmin.can_delete is True
    assert PortalQuizAttemptAdmin.can_create is False
    assert PortalQuizAttemptAdmin.can_edit is False
    assert PortalQuizAttemptAdmin.can_delete is True
