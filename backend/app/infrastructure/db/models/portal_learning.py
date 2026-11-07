from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import LearningMaterialStatus, LearningMaterialType, UserChecklistStatus
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.portal_user_profile import PortalUserProfile


def _enum_values(enum_cls: type) -> list[str]:
    return [e.value for e in enum_cls]  # type: ignore[attr-defined]


class PortalLearningMaterial(Base):
    """Учебный материал (статья, видео, презентация, инструкция)."""

    __tablename__ = "portal_learning_material"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_type: Mapped[str] = mapped_column(
        Enum(LearningMaterialType, values_callable=_enum_values, native_enum=False, length=32),
        nullable=False,
        server_default=LearningMaterialType.ARTICLE,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(LearningMaterialStatus, values_callable=_enum_values, native_enum=False, length=32),
        nullable=False,
        server_default=LearningMaterialStatus.DRAFT,
        index=True,
    )
    created_by_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    idp_group_rows: Mapped[list[PortalLearningMaterialIdpGroup]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    quizzes: Mapped[list[PortalQuiz]] = relationship("PortalQuiz", back_populates="material", lazy="noload")
    created_by_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalLearningMaterial.created_by_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )

    def __str__(self) -> str:
        return self.title


class PortalLearningMaterialIdpGroup(Base):
    """Связь учебного материала с группой Keycloak (строка claim)."""

    __tablename__ = "portal_learning_material_idp_group"

    material_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("portal_learning_material.id", ondelete="CASCADE"), primary_key=True
    )
    idp_group: Mapped[str] = mapped_column(String(255), primary_key=True)

    material: Mapped[PortalLearningMaterial] = relationship(back_populates="idp_group_rows")


class PortalChecklist(Base):
    """Шаблон чек-листа для онбординга/процессов."""

    __tablename__ = "portal_checklist"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Имя группы Keycloak (как в токене). Пустая строка = для всех авторизованных.
    idp_group: Mapped[str] = mapped_column(String(128), nullable=False, server_default="", index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    items: Mapped[list[PortalChecklistItem]] = relationship(
        "PortalChecklistItem",
        back_populates="checklist",
        order_by="PortalChecklistItem.order_index",
        lazy="noload",
    )
    user_checklists: Mapped[list[PortalUserChecklist]] = relationship(
        "PortalUserChecklist", back_populates="checklist", lazy="noload"
    )

    def __str__(self) -> str:
        return self.title


class PortalChecklistItem(Base):
    """Пункт чек-листа."""

    __tablename__ = "portal_checklist_item"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_checklist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")
    text: Mapped[str] = mapped_column(Text, nullable=False)

    checklist: Mapped[PortalChecklist] = relationship("PortalChecklist", back_populates="items", lazy="noload")
    user_item_marks: Mapped[list[PortalUserChecklistItem]] = relationship(
        "PortalUserChecklistItem", back_populates="item", lazy="noload"
    )

    def __str__(self) -> str:
        t = (self.text or "").replace("\n", " ").strip()
        return (t[:72] + "…") if len(t) > 72 else (t or "Пункт чек-листа")


class PortalUserChecklist(Base):
    """Прохождение чек-листа пользователем."""

    __tablename__ = "portal_user_checklist"
    __table_args__ = (UniqueConstraint("user_sub", "checklist_id", name="uq_portal_user_checklist_user_checklist"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    checklist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_checklist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        Enum(UserChecklistStatus, values_callable=_enum_values, native_enum=False, length=32),
        nullable=False,
        server_default=UserChecklistStatus.IN_PROGRESS,
        index=True,
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalUserChecklist.user_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )
    checklist: Mapped[PortalChecklist] = relationship(
        "PortalChecklist", back_populates="user_checklists", lazy="noload"
    )
    item_marks: Mapped[list[PortalUserChecklistItem]] = relationship(
        "PortalUserChecklistItem", back_populates="user_checklist", lazy="noload"
    )

    def __str__(self) -> str:
        checklist = getattr(self, "checklist", None)
        if checklist is not None and getattr(checklist, "title", None):
            return f"Прогресс: «{checklist.title}»"
        return "Прогресс по чек-листу"


class PortalUserChecklistItem(Base):
    """Отметка отдельного пункта чек-листа пользователем."""

    __tablename__ = "portal_user_checklist_item"
    __table_args__ = (UniqueConstraint("user_checklist_id", "item_id", name="uq_portal_user_checklist_item"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_checklist_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_user_checklist.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_checklist_item.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_checklist: Mapped[PortalUserChecklist] = relationship(
        "PortalUserChecklist", back_populates="item_marks", lazy="noload"
    )
    item: Mapped[PortalChecklistItem] = relationship(
        "PortalChecklistItem", back_populates="user_item_marks", lazy="noload"
    )


class PortalQuiz(Base):
    """Тест / квиз для проверки знаний."""

    __tablename__ = "portal_quiz"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    material_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_learning_material.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    material: Mapped[PortalLearningMaterial | None] = relationship(
        "PortalLearningMaterial", back_populates="quizzes", lazy="noload"
    )
    questions: Mapped[list[PortalQuizQuestion]] = relationship(
        "PortalQuizQuestion",
        back_populates="quiz",
        order_by="PortalQuizQuestion.order_index",
        lazy="noload",
    )
    attempts: Mapped[list[PortalQuizAttempt]] = relationship("PortalQuizAttempt", back_populates="quiz", lazy="noload")

    def __str__(self) -> str:
        return self.title


class PortalQuizQuestion(Base):
    """Вопрос теста."""

    __tablename__ = "portal_quiz_question"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_quiz.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    order_index: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default="0")

    quiz: Mapped[PortalQuiz] = relationship("PortalQuiz", back_populates="questions", lazy="noload")
    answers: Mapped[list[PortalQuizAnswer]] = relationship(
        "PortalQuizAnswer", back_populates="question", order_by="PortalQuizAnswer.id", lazy="noload"
    )
    attempt_answers: Mapped[list[PortalQuizAttemptAnswer]] = relationship(
        "PortalQuizAttemptAnswer", back_populates="question", lazy="noload"
    )

    def __str__(self) -> str:
        t = (self.text or "").replace("\n", " ").strip()
        return (t[:80] + "…") if len(t) > 80 else (t or str(self.id))


class PortalQuizAnswer(Base):
    """Вариант ответа на вопрос теста."""

    __tablename__ = "portal_quiz_answer"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_quiz_question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    question: Mapped[PortalQuizQuestion] = relationship("PortalQuizQuestion", back_populates="answers", lazy="noload")

    def __str__(self) -> str:
        t = (self.text or "").strip()
        return (t[:48] + "…") if len(t) > 48 else (t or "Вариант ответа")


class PortalQuizAttempt(Base):
    """Попытка прохождения теста пользователем."""

    __tablename__ = "portal_quiz_attempt"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_sub: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    quiz_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_quiz.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    max_score: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user_profile: Mapped[PortalUserProfile | None] = relationship(
        "PortalUserProfile",
        primaryjoin="PortalQuizAttempt.user_sub == foreign(PortalUserProfile.sub)",
        viewonly=True,
        lazy="selectin",
    )
    quiz: Mapped[PortalQuiz] = relationship("PortalQuiz", back_populates="attempts", lazy="noload")
    attempt_answers: Mapped[list[PortalQuizAttemptAnswer]] = relationship(
        "PortalQuizAttemptAnswer", back_populates="attempt", lazy="noload"
    )

    def __str__(self) -> str:
        quiz = getattr(self, "quiz", None)
        if quiz is not None and getattr(quiz, "title", None):
            return f"Попытка: «{quiz.title}»"
        return "Попытка теста"


class PortalQuizAttemptAnswer(Base):
    """Ответ пользователя на вопрос в попытке теста.

    UNIQUE(attempt_id, question_id) — защита от гонки при параллельном повторном
    `submit_attempt` одной и той же попытки (см. services/quiz.py): второй параллельный
    коммит получит IntegrityError -> ConflictError, вместо задвоенных строк ответов.
    """

    __tablename__ = "portal_quiz_attempt_answer"
    __table_args__ = (UniqueConstraint("attempt_id", "question_id", name="uq_quiz_attempt_answer_attempt_question"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_quiz_attempt.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_quiz_question.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    answer_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("portal_quiz_answer.id", ondelete="SET NULL"),
        nullable=True,
    )

    attempt: Mapped[PortalQuizAttempt] = relationship(
        "PortalQuizAttempt", back_populates="attempt_answers", lazy="noload"
    )
    question: Mapped[PortalQuizQuestion] = relationship(
        "PortalQuizQuestion", back_populates="attempt_answers", lazy="noload"
    )
