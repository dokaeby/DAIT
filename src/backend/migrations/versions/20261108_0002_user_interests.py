"""user_interests 테이블을 만든다. users는 이 테이블을 모른다(관심사만 따로 뗄 수 있게).

Revision ID: 0002_interests
Revises: 0001_users
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_interests"
down_revision = "0001_users"
branch_labels = None
depends_on = None


# 입력: 사용자 테이블이 생성된 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 사용자별 중복을 막는 관심사 연결 테이블을 생성한다.
def upgrade() -> None:
    """user_interests를 만든다(SQLite·PostgreSQL 공통 문법만 사용).

    입력: 없음
    출력: 없음
    기능: (user_id, interest_code)를 기본키로 두어 중복을 막고 사용자별 조회를 빠르게 한다.
          탈퇴 시 자동으로 지워지도록 users 삭제에 CASCADE를 건다.
          코드 값 검증은 Pydantic Enum이 맡는다.
    """
    op.create_table(
        "user_interests",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("interest_code", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "interest_code", name="pk_user_interests"),
    )


# 입력: 관심사 연결 테이블이 있는 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 사용자 계정은 유지하고 관심사 연결 테이블만 제거한다.
def downgrade() -> None:
    """user_interests만 지운다.

    입력: 없음
    출력: 없음
    기능: 가입·로그인에 쓰는 users, refresh_tokens는 건드리지 않는다.
    """
    op.drop_table("user_interests")
