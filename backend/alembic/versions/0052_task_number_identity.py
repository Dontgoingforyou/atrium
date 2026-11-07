"""Порядковый номер задачи: number GENERATED ALWAYS AS IDENTITY."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0052_task_number_identity"
down_revision = "0051_attachment_voice_meta"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем колонку без ограничений — сначала заполним существующие строки
    op.add_column(
        "portal_task",
        sa.Column("number", sa.Integer(), nullable=True),
    )
    # Нумеруем существующие строки по дате создания (порядковые номера с 1)
    op.execute(
        """
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS rn
            FROM portal_task
        )
        UPDATE portal_task SET number = ranked.rn
        FROM ranked
        WHERE portal_task.id = ranked.id
        """
    )
    # Делаем колонку NOT NULL и добавляем IDENTITY с нужным стартом
    op.execute("ALTER TABLE portal_task ALTER COLUMN number SET NOT NULL")
    op.execute(
        """
        DO $$
        DECLARE
            next_val BIGINT;
        BEGIN
            SELECT COALESCE(MAX(number), 0) + 1 INTO next_val FROM portal_task;
            EXECUTE format(
                'ALTER TABLE portal_task ALTER COLUMN number ADD GENERATED ALWAYS AS IDENTITY (START WITH %s)',
                next_val
            );
        END $$
        """
    )
    op.create_index("ix_portal_task_number", "portal_task", ["number"])


def downgrade() -> None:
    op.drop_index("ix_portal_task_number", table_name="portal_task")
    op.execute("ALTER TABLE portal_task ALTER COLUMN number DROP IDENTITY IF EXISTS")
    op.drop_column("portal_task", "number")
