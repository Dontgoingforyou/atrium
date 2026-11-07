"""portal_specialist_profile: Jira issue link; portal_specialist_column: jira_status_id."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0067_specialist_jira"
down_revision = "0066_userprofile_is_developer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portal_specialist_profile",
        sa.Column("jira_issue_key", sa.String(32), nullable=True),
    )
    op.add_column(
        "portal_specialist_profile",
        sa.Column("jira_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "portal_specialist_profile",
        sa.Column(
            "jira_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index(
        "ix_portal_specialist_profile_jira_issue_key",
        "portal_specialist_profile",
        ["jira_issue_key"],
        unique=True,
    )

    op.add_column(
        "portal_specialist_column",
        sa.Column("jira_status_id", sa.String(20), nullable=True),
    )
    op.create_index(
        "ix_portal_specialist_column_jira_status_id",
        "portal_specialist_column",
        ["jira_status_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_portal_specialist_column_jira_status_id", table_name="portal_specialist_column")
    op.drop_column("portal_specialist_column", "jira_status_id")
    op.drop_index("ix_portal_specialist_profile_jira_issue_key", table_name="portal_specialist_profile")
    op.drop_column("portal_specialist_profile", "jira_fields")
    op.drop_column("portal_specialist_profile", "jira_synced_at")
    op.drop_column("portal_specialist_profile", "jira_issue_key")
