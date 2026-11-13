"""Track the first-login interest invitation for newly registered accounts only."""

import sqlalchemy as sa
from alembic import op

revision = "0006_interest_onboarding"
down_revision = "0005_news_reads"
branch_labels = None
depends_on = None


# 입력: 사용자 테이블이 생성된 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 신규 사용자의 최초 관심사 안내 대기 테이블을 생성한다.
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


# 입력: 관심사 안내 대기 테이블이 있는 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 계정과 저장 관심사는 유지하고 안내 대기 테이블만 제거한다.
def downgrade() -> None:
    """Remove pending invitations without changing accounts or saved interests."""
    op.drop_table("pending_interest_onboarding")
