"""Track the first-login interest invitation for newly registered accounts only."""

import sqlalchemy as sa
from alembic import op

revision = "0006_interest_onboarding"
down_revision = "0005_news_reads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Existing accounts are not enrolled retroactively."""
    op.create_table(
        "pending_interest_onboarding",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    """Remove pending invitations without changing accounts or saved interests."""
    op.drop_table("pending_interest_onboarding")
