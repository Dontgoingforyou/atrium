from app.portal_learning.admin.checklist import (
    PortalChecklistAdmin,
    PortalChecklistItemAdmin,
    PortalUserChecklistAdmin,
)
from app.portal_learning.admin.material import PortalLearningMaterialAdmin
from app.portal_learning.admin.quiz import (
    PortalQuizAdmin,
    PortalQuizAnswerAdmin,
    PortalQuizAttemptAdmin,
    PortalQuizQuestionAdmin,
)

__all__ = [
    "PortalLearningMaterialAdmin",
    "PortalChecklistAdmin",
    "PortalChecklistItemAdmin",
    "PortalUserChecklistAdmin",
    "PortalQuizAdmin",
    "PortalQuizQuestionAdmin",
    "PortalQuizAnswerAdmin",
    "PortalQuizAttemptAdmin",
]
