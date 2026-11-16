"""구글 로그인 연결(social_identities)을 만들고 비밀번호 없는 계정을 허용한다.

Revision ID: 0008_social_identities
Revises: 0007_merge_schedule_onboarding
Create Date: 2026-11-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_social_identities"
down_revision = "0007_merge_schedule_onboarding"
branch_labels = None
depends_on = None

_PASSWORDLESS_LEFT = (
    "비밀번호 없는 소셜 계정이 남아 있어 password_hash를 NOT NULL로 되돌릴 수 없습니다. "
    "해당 계정을 정리한 뒤 다시 실행하세요."
)


# 입력: 0007까지 적용된 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 소셜 연결 테이블을 만들고 users.password_hash를 NULL 허용으로 바꾼다.
def upgrade() -> None:
    """social_identities를 만들고 비밀번호 해시를 선택값으로 바꾼다.

    입력: 없음
    출력: 없음
    기능: (provider, subject) 유니크로 한 구글 계정이 두 사용자에 붙지 않게 하고,
          (user_id, provider) 유니크로 한 사용자에 구글 계정이 하나만 붙게 한다.
          탈퇴하면 연결도 CASCADE로 함께 지워진다.
    """
    op.create_table(
        "social_identities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(16), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("provider IN ('GOOGLE')", name="ck_social_identities_provider"),
        sa.UniqueConstraint("provider", "subject", name="uq_social_identities_provider_subject"),
        sa.UniqueConstraint("user_id", "provider", name="uq_social_identities_user_provider"),
    )
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_hash", existing_type=sa.String(255), nullable=True)


# 입력: 0008이 적용된 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 비밀번호 없는 계정이 없을 때만 NOT NULL을 복구하고 연결 테이블을 지운다.
def downgrade() -> None:
    """만든 것을 되돌린다. 데이터는 자동으로 지우지 않는다.

    입력: 없음
    출력: 없음
    기능: password_hash가 NULL인 사용자가 있으면 RuntimeError로 멈춰 계정 손실을 막는다.
    """
    left = (
        op.get_bind()
        .execute(sa.text("SELECT COUNT(*) FROM users WHERE password_hash IS NULL"))
        .scalar_one()
    )
    if left:
        raise RuntimeError(_PASSWORDLESS_LEFT)
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_table("social_identities")
