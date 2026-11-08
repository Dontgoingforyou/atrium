"""Jira outbound fields for portal tasks (TASKS).

Revision ID: 0091_task_jira_outbound
Revises: 0090_drop_user_avatar_cols
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0091_task_jira_outbound"
down_revision = "0090_drop_user_avatar_cols"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("portal_task", sa.Column("jira_issue_key", sa.String(length=32), nullable=True))
    op.add_column("portal_task", sa.Column("jira_issue_id", sa.String(length=32), nullable=True))
    op.add_column("portal_task", sa.Column("jira_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("portal_task", sa.Column("jira_sync_error", sa.Text(), nullable=True))
    op.create_index("ix_portal_task_jira_issue_key", "portal_task", ["jira_issue_key"], unique=True)

    op.add_column("portal_task_column", sa.Column("jira_status_id", sa.String(length=32), nullable=True))
    op.create_index("ix_portal_task_column_jira_status_id", "portal_task_column", ["jira_status_id"], unique=False)

    op.add_column("portal_task_comment", sa.Column("jira_comment_id", sa.String(length=64), nullable=True))
    op.create_index("ix_portal_task_comment_jira_comment_id", "portal_task_comment", ["jira_comment_id"], unique=False)

    op.add_column("portal_task_file", sa.Column("jira_attachment_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("portal_task_file", "jira_attachment_id")
    op.drop_index("ix_portal_task_comment_jira_comment_id", table_name="portal_task_comment")
    op.drop_column("portal_task_comment", "jira_comment_id")
    op.drop_index("ix_portal_task_column_jira_status_id", table_name="portal_task_column")
    op.drop_column("portal_task_column", "jira_status_id")
    op.drop_index("ix_portal_task_jira_issue_key", table_name="portal_task")
    op.drop_column("portal_task", "jira_sync_error")
    op.drop_column("portal_task", "jira_synced_at")
    op.drop_column("portal_task", "jira_issue_id")
    op.drop_column("portal_task", "jira_issue_key")
