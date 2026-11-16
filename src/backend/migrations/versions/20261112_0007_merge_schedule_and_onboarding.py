"""Merge the schedule-run and interest-onboarding migration branches."""

revision = "0007_merge_schedule_onboarding"
down_revision = ("0004_schedule_runs", "0006_interest_onboarding")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join both schema histories without changing existing tables."""


def downgrade() -> None:
    """Restore the two independent migration heads."""
