"""portal_specialist_profile: direction из Jira (вместо portal_specialist_status)."""

from __future__ import annotations

from alembic import op

revision = "0068_spec_profile_direction"
down_revision = "0067_specialist_jira"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS: upgrade мог частично примениться до падения записи version_num (VARCHAR(32)).
    op.execute("ALTER TABLE portal_specialist_profile ADD COLUMN IF NOT EXISTS direction VARCHAR(255)")


def downgrade() -> None:
    op.execute("ALTER TABLE portal_specialist_profile DROP COLUMN IF EXISTS direction")
