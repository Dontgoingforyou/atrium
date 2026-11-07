"""Чаты, задачи, договорённости портала (эпики 11–13).

Revision ID: 0010_portal_chat_task_agreement
Revises: 0009_portal_favorite
Create Date: 2026-04-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_portal_chat_task_agreement"
down_revision: str | Sequence[str] | None = "0009_portal_favorite"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "portal_chat",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("created_by_sub", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("nav_node_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nav_node_id"], ["portal_nav_node.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portal_chat_created_by_sub"), "portal_chat", ["created_by_sub"], unique=False)
    op.create_index(op.f("ix_portal_chat_nav_node_id"), "portal_chat", ["nav_node_id"], unique=False)
    op.create_index(op.f("ix_portal_chat_document_id"), "portal_chat", ["document_id"], unique=False)

    op.create_table(
        "portal_chat_member",
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("user_sub", sa.String(length=255), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chat_id", "user_sub"),
    )

    op.create_table(
        "portal_chat_message",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("chat_id", sa.Uuid(), nullable=False),
        sa.Column("author_sub", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chat.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portal_chat_message_chat_id"), "portal_chat_message", ["chat_id"], unique=False)
    op.create_index(op.f("ix_portal_chat_message_author_sub"), "portal_chat_message", ["author_sub"], unique=False)

    op.create_table(
        "portal_task",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("creator_sub", sa.String(length=255), nullable=False),
        sa.Column("assignee_sub", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="todo"),
        sa.Column("priority", sa.String(length=16), nullable=False, server_default="medium"),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("nav_node_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("source_message_id", sa.Uuid(), nullable=True),
        sa.Column("chat_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["chat_id"], ["portal_chat.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nav_node_id"], ["portal_nav_node.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["portal_chat_message.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portal_task_creator_sub"), "portal_task", ["creator_sub"], unique=False)
    op.create_index(op.f("ix_portal_task_assignee_sub"), "portal_task", ["assignee_sub"], unique=False)
    op.create_index(op.f("ix_portal_task_status"), "portal_task", ["status"], unique=False)
    op.create_index(op.f("ix_portal_task_priority"), "portal_task", ["priority"], unique=False)
    op.create_index(op.f("ix_portal_task_nav_node_id"), "portal_task", ["nav_node_id"], unique=False)
    op.create_index(op.f("ix_portal_task_document_id"), "portal_task", ["document_id"], unique=False)
    op.create_index(op.f("ix_portal_task_source_message_id"), "portal_task", ["source_message_id"], unique=False)
    op.create_index(op.f("ix_portal_task_chat_id"), "portal_task", ["chat_id"], unique=False)

    op.create_table(
        "portal_task_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("changed_by_sub", sa.String(length=255), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_portal_task_history_task_id"), "portal_task_history", ["task_id"], unique=False)

    op.create_table(
        "portal_agreement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("source_message_id", sa.Uuid(), nullable=True),
        sa.Column("nav_node_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_sub", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["portal_document.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["nav_node_id"], ["portal_nav_node.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_message_id"], ["portal_chat_message.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["task_id"], ["portal_task.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_portal_agreement_status"),
        "portal_agreement",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_portal_agreement_source_message_id"),
        "portal_agreement",
        ["source_message_id"],
        unique=False,
    )
    op.create_index(op.f("ix_portal_agreement_nav_node_id"), "portal_agreement", ["nav_node_id"], unique=False)
    op.create_index(op.f("ix_portal_agreement_document_id"), "portal_agreement", ["document_id"], unique=False)
    op.create_index(op.f("ix_portal_agreement_task_id"), "portal_agreement", ["task_id"], unique=False)
    op.create_index(op.f("ix_portal_agreement_created_by_sub"), "portal_agreement", ["created_by_sub"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_portal_agreement_created_by_sub"), table_name="portal_agreement")
    op.drop_index(op.f("ix_portal_agreement_task_id"), table_name="portal_agreement")
    op.drop_index(op.f("ix_portal_agreement_document_id"), table_name="portal_agreement")
    op.drop_index(op.f("ix_portal_agreement_nav_node_id"), table_name="portal_agreement")
    op.drop_index(op.f("ix_portal_agreement_source_message_id"), table_name="portal_agreement")
    op.drop_index(op.f("ix_portal_agreement_status"), table_name="portal_agreement")
    op.drop_table("portal_agreement")

    op.drop_index(op.f("ix_portal_task_history_task_id"), table_name="portal_task_history")
    op.drop_table("portal_task_history")

    op.drop_index(op.f("ix_portal_task_chat_id"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_source_message_id"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_document_id"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_nav_node_id"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_priority"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_status"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_assignee_sub"), table_name="portal_task")
    op.drop_index(op.f("ix_portal_task_creator_sub"), table_name="portal_task")
    op.drop_table("portal_task")

    op.drop_index(op.f("ix_portal_chat_message_author_sub"), table_name="portal_chat_message")
    op.drop_index(op.f("ix_portal_chat_message_chat_id"), table_name="portal_chat_message")
    op.drop_table("portal_chat_message")

    op.drop_table("portal_chat_member")

    op.drop_index(op.f("ix_portal_chat_document_id"), table_name="portal_chat")
    op.drop_index(op.f("ix_portal_chat_nav_node_id"), table_name="portal_chat")
    op.drop_index(op.f("ix_portal_chat_created_by_sub"), table_name="portal_chat")
    op.drop_table("portal_chat")
