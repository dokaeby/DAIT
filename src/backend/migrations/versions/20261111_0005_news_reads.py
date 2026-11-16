"""Persist account article read history."""

import sqlalchemy as sa
from alembic import op

revision = "0005_news_reads"
down_revision = "0004_user_nickname"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create account-owned, idempotent read records."""
    op.create_table(
        "news_reads",
        sa.Column(
            "user_id",
            sa.String(64),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "news_id", sa.String(64), sa.ForeignKey("news.id", ondelete="CASCADE"), primary_key=True
        ),
    )


def downgrade() -> None:
    """Remove read records."""
    op.drop_table("news_reads")
