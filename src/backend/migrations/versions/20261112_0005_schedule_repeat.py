"""예약 반복 방식(매일·요일 선택·한 번만)을 저장할 칸을 추가한다.

Revision ID: 0005_schedule_repeat
Revises: 0004_schedule_runs
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_schedule_repeat"
down_revision = "0004_schedule_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """schedules에 repeat·weekdays·run_date를 추가한다.

    입력: 없음
    출력: 없음
    기능: 기존 예약은 모두 매일(DAILY)로 남도록 기본값을 둔다.
          weekdays는 월=0…일=6 정수 JSON 배열, run_date는 한 번만 예약의 날짜(YYYY-MM-DD)다.
    """
    with op.batch_alter_table("schedules") as batch:
        batch.add_column(sa.Column("repeat", sa.String(10), nullable=False, server_default="DAILY"))
        batch.add_column(sa.Column("weekdays", sa.Text(), nullable=False, server_default="[]"))
        batch.add_column(sa.Column("run_date", sa.String(10), nullable=True))


def downgrade() -> None:
    """추가한 칸을 지운다."""
    with op.batch_alter_table("schedules") as batch:
        batch.drop_column("run_date")
        batch.drop_column("weekdays")
        batch.drop_column("repeat")
