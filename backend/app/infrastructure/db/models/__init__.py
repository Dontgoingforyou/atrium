"""ORM-модели (импорт для регистрации в metadata Alembic)."""

from app.infrastructure.db.models.portal_agreement import PortalAgreement
from app.infrastructure.db.models.portal_bench import PortalBenchSyncState, PortalBenchYearSnapshot
from app.infrastructure.db.models.portal_calendar import (
    PortalCalendar,
    PortalCalendarAttendee,
    PortalCalendarEvent,
    PortalCalendarEventOverride,
    PortalCalendarInviteToken,
    PortalCalendarMember,
    PortalCalendarReminder,
    PortalCalendarReminderSent,
)
from app.infrastructure.db.models.portal_calendar_fact import PortalCalendarFact
from app.infrastructure.db.models.portal_chat import (
    PortalChat,
    PortalChatMember,
    PortalChatMessage,
    PortalChatMessageHidden,
    PortalChatMessageReaction,
)
from app.infrastructure.db.models.portal_document import (
    PortalDocument,
    PortalDocumentFile,
    PortalDocumentHistory,
    PortalDocumentShortcut,
    PortalDocumentTag,
    PortalTag,
)
from app.infrastructure.db.models.portal_document_comment import (
    PortalDocumentComment,
    PortalDocumentCommentMedia,
)
from app.infrastructure.db.models.portal_embedding import PortalEmbedding
from app.infrastructure.db.models.portal_favorite import PortalFavorite
from app.infrastructure.db.models.portal_finance import (
    PortalContract,
    PortalCounterparty,
    PortalInvoice,
    PortalPayment,
)
from app.infrastructure.db.models.portal_learning import (
    PortalChecklist,
    PortalChecklistItem,
    PortalLearningMaterial,
    PortalLearningMaterialIdpGroup,
    PortalQuiz,
    PortalQuizAnswer,
    PortalQuizAttempt,
    PortalQuizAttemptAnswer,
    PortalQuizQuestion,
    PortalUserChecklist,
    PortalUserChecklistItem,
)
from app.infrastructure.db.models.portal_manager_specialist import PortalManagerSpecialist
from app.infrastructure.db.models.portal_notification import PortalNotification
from app.infrastructure.db.models.portal_rich_media import PortalRichMedia
from app.infrastructure.db.models.portal_specialist_column import PortalSpecialistColumn
from app.infrastructure.db.models.portal_specialist_jira_status_map import PortalSpecialistJiraStatusMap
from app.infrastructure.db.models.portal_specialist_link import PortalSpecialistLink
from app.infrastructure.db.models.portal_specialist_note import (
    PortalSpecialistNote,
    PortalSpecialistNoteMedia,
)
from app.infrastructure.db.models.portal_specialist_profile import PortalSpecialistProfile
from app.infrastructure.db.models.portal_specialist_status import PortalSpecialistStatus
from app.infrastructure.db.models.portal_task import PortalTask, PortalTaskComment, PortalTaskHistory, PortalTaskTag
from app.infrastructure.db.models.portal_task_assignee import PortalTaskAssignee
from app.infrastructure.db.models.portal_task_reminder_sent import PortalTaskReminderSent
from app.infrastructure.db.models.portal_telegram_binding import PortalTelegramBinding
from app.infrastructure.db.models.portal_time_entry import PortalTimeEntry
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile
from app.infrastructure.db.models.portal_user_specialist_board_pref import PortalUserSpecialistBoardPref
from app.infrastructure.db.models.portal_user_task_board_pref import PortalUserTaskBoardPref
from app.infrastructure.db.models.portal_web_push import PortalWebPushSubscription

__all__ = [
    "PortalAgreement",
    "PortalBenchSyncState",
    "PortalBenchYearSnapshot",
    "PortalCalendar",
    "PortalCalendarFact",
    "PortalCalendarAttendee",
    "PortalCalendarEvent",
    "PortalCalendarEventOverride",
    "PortalCalendarInviteToken",
    "PortalCalendarMember",
    "PortalCalendarReminder",
    "PortalCalendarReminderSent",
    "PortalChat",
    "PortalChatMember",
    "PortalChatMessage",
    "PortalChatMessageHidden",
    "PortalChatMessageReaction",
    "PortalEmbedding",
    "PortalFavorite",
    "PortalNotification",
    "PortalRichMedia",
    "PortalTelegramBinding",
    "PortalDocument",
    "PortalDocumentComment",
    "PortalDocumentCommentMedia",
    "PortalDocumentFile",
    "PortalTag",
    "PortalDocumentTag",
    "PortalDocumentHistory",
    "PortalDocumentShortcut",
    "PortalManagerSpecialist",
    "PortalSpecialistColumn",
    "PortalSpecialistJiraStatusMap",
    "PortalSpecialistLink",
    "PortalSpecialistNote",
    "PortalSpecialistNoteMedia",
    "PortalSpecialistProfile",
    "PortalSpecialistStatus",
    "PortalTask",
    "PortalTaskAssignee",
    "PortalTaskReminderSent",
    "PortalTaskComment",
    "PortalTaskHistory",
    "PortalTaskTag",
    "PortalTimeEntry",
    "PortalUserProfile",
    "PortalUserSpecialistBoardPref",
    "PortalUserTaskBoardPref",
    "PortalWebPushSubscription",
    "PortalCounterparty",
    "PortalContract",
    "PortalInvoice",
    "PortalPayment",
    "PortalLearningMaterial",
    "PortalLearningMaterialIdpGroup",
    "PortalChecklist",
    "PortalChecklistItem",
    "PortalUserChecklist",
    "PortalUserChecklistItem",
    "PortalQuiz",
    "PortalQuizQuestion",
    "PortalQuizAnswer",
    "PortalQuizAttempt",
    "PortalQuizAttemptAnswer",
]
