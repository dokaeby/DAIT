"""선택 닉네임과 동시 가입 중복을 막는 유니크 인덱스를 추가한다."""

import sqlalchemy as sa
from alembic import op

revision = "0004_user_nickname"
down_revision = "0003_news_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """기존 사용자는 NULL을 유지하므로 이메일 표시가 보존된다."""
    op.add_column("users", sa.Column("nickname", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("nickname_key", sa.String(90), nullable=True))
    op.create_index("uq_users_nickname_key", "users", ["nickname_key"], unique=True)


def downgrade() -> None:
    """닉네임만 제거하고 기존 계정은 유지한다."""
    op.drop_index("uq_users_nickname_key", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("nickname_key")
        batch.drop_column("nickname")
