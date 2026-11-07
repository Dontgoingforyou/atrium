"""Обучение и проверка знаний (эпик 18).

Таблицы:
- portal_learning_material  — учебные материалы
- portal_checklist          — шаблоны чек-листов
- portal_checklist_item     — пункты чек-листов
- portal_user_checklist     — прохождение чек-листа пользователем
- portal_user_checklist_item — отметка пунктов пользователем
- portal_quiz               — тесты/квизы
- portal_quiz_question      — вопросы теста
- portal_quiz_answer        — варианты ответов
- portal_quiz_attempt       — попытки прохождения теста
- portal_quiz_attempt_answer — ответы пользователя в попытке

Revision ID: 0016_portal_learning
Revises: 0015_portal_procurement
Create Date: 2026-04-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_portal_learning"
down_revision: str | None = "0015_portal_procurement"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── 1. portal_learning_material ────────────────────────────────────────────
    op.create_table(
        "portal_learning_material",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column(
            "material_type",
            sa.String(32),
            nullable=False,
            server_default="article",
        ),
        sa.Column(
            "status",
            sa.String(32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("role_slugs_json", sa.Text, nullable=False, server_default="[]"),
        sa.Column(
            "nav_node_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_nav_node.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_by_sub", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_learning_material_title", "portal_learning_material", ["title"])
    op.create_index("ix_portal_learning_material_material_type", "portal_learning_material", ["material_type"])
    op.create_index("ix_portal_learning_material_status", "portal_learning_material", ["status"])
    op.create_index("ix_portal_learning_material_nav_node_id", "portal_learning_material", ["nav_node_id"])
    op.create_index("ix_portal_learning_material_created_by_sub", "portal_learning_material", ["created_by_sub"])

    # ── 2. portal_checklist ────────────────────────────────────────────────────
    op.create_table(
        "portal_checklist",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("role_slug", sa.String(128), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_checklist_role_slug", "portal_checklist", ["role_slug"])

    # ── 3. portal_checklist_item ───────────────────────────────────────────────
    op.create_table(
        "portal_checklist_item",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "checklist_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_checklist.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("order_index", sa.SmallInteger, nullable=False, server_default="0"),
        sa.Column("text", sa.Text, nullable=False),
    )
    op.create_index("ix_portal_checklist_item_checklist_id", "portal_checklist_item", ["checklist_id"])

    # ── 4. portal_user_checklist ───────────────────────────────────────────────
    op.create_table(
        "portal_user_checklist",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column(
            "checklist_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_checklist.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="in_progress"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_portal_user_checklist_user_sub", "portal_user_checklist", ["user_sub"])
    op.create_index("ix_portal_user_checklist_checklist_id", "portal_user_checklist", ["checklist_id"])
    op.create_index(
        "uq_portal_user_checklist_user_checklist",
        "portal_user_checklist",
        ["user_sub", "checklist_id"],
        unique=True,
    )

    # ── 5. portal_user_checklist_item ──────────────────────────────────────────
    op.create_table(
        "portal_user_checklist_item",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "user_checklist_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_user_checklist.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_checklist_item.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("is_done", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_portal_user_checklist_item_user_checklist_id",
        "portal_user_checklist_item",
        ["user_checklist_id"],
    )
    op.create_index("ix_portal_user_checklist_item_item_id", "portal_user_checklist_item", ["item_id"])
    op.create_index(
        "uq_portal_user_checklist_item",
        "portal_user_checklist_item",
        ["user_checklist_id", "item_id"],
        unique=True,
    )

    # ── 6. portal_quiz ─────────────────────────────────────────────────────────
    op.create_table(
        "portal_quiz",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "material_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_learning_material.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_portal_quiz_material_id", "portal_quiz", ["material_id"])

    # ── 7. portal_quiz_question ────────────────────────────────────────────────
    op.create_table(
        "portal_quiz_question",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "quiz_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_quiz.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("order_index", sa.SmallInteger, nullable=False, server_default="0"),
    )
    op.create_index("ix_portal_quiz_question_quiz_id", "portal_quiz_question", ["quiz_id"])

    # ── 8. portal_quiz_answer ──────────────────────────────────────────────────
    op.create_table(
        "portal_quiz_answer",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "question_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_quiz_question.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("is_correct", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_portal_quiz_answer_question_id", "portal_quiz_answer", ["question_id"])

    # ── 9. portal_quiz_attempt ─────────────────────────────────────────────────
    op.create_table(
        "portal_quiz_attempt",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("user_sub", sa.String(255), nullable=False),
        sa.Column(
            "quiz_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_quiz.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("max_score", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_portal_quiz_attempt_user_sub", "portal_quiz_attempt", ["user_sub"])
    op.create_index("ix_portal_quiz_attempt_quiz_id", "portal_quiz_attempt", ["quiz_id"])

    # ── 10. portal_quiz_attempt_answer ─────────────────────────────────────────
    op.create_table(
        "portal_quiz_attempt_answer",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_quiz_attempt.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_quiz_question.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "answer_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("portal_quiz_answer.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_portal_quiz_attempt_answer_attempt_id", "portal_quiz_attempt_answer", ["attempt_id"])
    op.create_index("ix_portal_quiz_attempt_answer_question_id", "portal_quiz_attempt_answer", ["question_id"])
    op.create_index(
        "uq_portal_quiz_attempt_answer",
        "portal_quiz_attempt_answer",
        ["attempt_id", "question_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_portal_quiz_attempt_answer", table_name="portal_quiz_attempt_answer")
    op.drop_index("ix_portal_quiz_attempt_answer_question_id", table_name="portal_quiz_attempt_answer")
    op.drop_index("ix_portal_quiz_attempt_answer_attempt_id", table_name="portal_quiz_attempt_answer")
    op.drop_table("portal_quiz_attempt_answer")

    op.drop_index("ix_portal_quiz_attempt_quiz_id", table_name="portal_quiz_attempt")
    op.drop_index("ix_portal_quiz_attempt_user_sub", table_name="portal_quiz_attempt")
    op.drop_table("portal_quiz_attempt")

    op.drop_index("ix_portal_quiz_answer_question_id", table_name="portal_quiz_answer")
    op.drop_table("portal_quiz_answer")

    op.drop_index("ix_portal_quiz_question_quiz_id", table_name="portal_quiz_question")
    op.drop_table("portal_quiz_question")

    op.drop_index("ix_portal_quiz_material_id", table_name="portal_quiz")
    op.drop_table("portal_quiz")

    op.drop_index("uq_portal_user_checklist_item", table_name="portal_user_checklist_item")
    op.drop_index("ix_portal_user_checklist_item_item_id", table_name="portal_user_checklist_item")
    op.drop_index("ix_portal_user_checklist_item_user_checklist_id", table_name="portal_user_checklist_item")
    op.drop_table("portal_user_checklist_item")

    op.drop_index("uq_portal_user_checklist_user_checklist", table_name="portal_user_checklist")
    op.drop_index("ix_portal_user_checklist_checklist_id", table_name="portal_user_checklist")
    op.drop_index("ix_portal_user_checklist_user_sub", table_name="portal_user_checklist")
    op.drop_table("portal_user_checklist")

    op.drop_index("ix_portal_checklist_item_checklist_id", table_name="portal_checklist_item")
    op.drop_table("portal_checklist_item")

    op.drop_index("ix_portal_checklist_role_slug", table_name="portal_checklist")
    op.drop_table("portal_checklist")

    op.drop_index("ix_portal_learning_material_created_by_sub", table_name="portal_learning_material")
    op.drop_index("ix_portal_learning_material_nav_node_id", table_name="portal_learning_material")
    op.drop_index("ix_portal_learning_material_status", table_name="portal_learning_material")
    op.drop_index("ix_portal_learning_material_material_type", table_name="portal_learning_material")
    op.drop_index("ix_portal_learning_material_title", table_name="portal_learning_material")
    op.drop_table("portal_learning_material")
