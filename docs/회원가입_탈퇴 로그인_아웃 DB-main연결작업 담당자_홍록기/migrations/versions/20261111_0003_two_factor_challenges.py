"""two_factor_challenges 테이블을 만든다. users는 이 테이블을 모른다(2차 인증만 따로 뗄 수 있게).

Revision ID: 0003_two_factor
Revises: 0002_interests
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_two_factor"
down_revision = "0002_interests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """two_factor_challenges를 만든다(SQLite·PostgreSQL 공통 문법만 사용).

    입력: 없음
    출력: 없음
    기능: 코드 원문은 저장하지 않고 키를 섞은 해시(code_hash)만 둔다. 기본키 key는
          challenge_id의 SHA-256이라 DB가 유출돼도 챌린지를 쓸 수 없다. 탈퇴 시 자동으로
          지워지도록 users 삭제에 CASCADE를 건다. 시각은 UTC ISO 문자열로 저장한다.
    """
    op.create_table(
        "two_factor_challenges",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.String(40), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("resend_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_sent_at", sa.String(40), nullable=False),
        sa.Column("created_at", sa.String(40), nullable=False),
    )
    op.create_index("ix_two_factor_challenges_user_id", "two_factor_challenges", ["user_id"])
    op.create_index("ix_two_factor_challenges_expires_at", "two_factor_challenges", ["expires_at"])


def downgrade() -> None:
    """two_factor_challenges만 지운다.

    입력: 없음
    출력: 없음
    기능: 가입·로그인·관심사 테이블은 건드리지 않는다.
    """
    op.drop_index("ix_two_factor_challenges_expires_at", table_name="two_factor_challenges")
    op.drop_index("ix_two_factor_challenges_user_id", table_name="two_factor_challenges")
    op.drop_table("two_factor_challenges")
