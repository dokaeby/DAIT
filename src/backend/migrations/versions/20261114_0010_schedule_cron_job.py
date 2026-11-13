"""schedules에 cron-job.org job id를 저장할 컬럼을 추가한다.

Revision ID: 0010_schedule_cron_job
Revises: 0009_merge_social_topics
Create Date: 2026-11-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_schedule_cron_job"
down_revision = "0009_merge_social_topics"
branch_labels = None
depends_on = None


# 입력: schedules 테이블이 있는 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 외부 cron job id를 nullable 컬럼으로 추가한다(기존 예약은 NULL로 남는다).
def upgrade() -> None:
    """schedules.cron_job_id 컬럼을 추가한다.

    입력: 없음
    출력: 없음
    기능: 예약과 cron-job.org job을 연결할 id를 저장한다.
    """
    with op.batch_alter_table("schedules") as batch:
        batch.add_column(sa.Column("cron_job_id", sa.String(64), nullable=True))


# 입력: 컬럼이 추가된 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: cron_job_id 컬럼을 제거한다.
def downgrade() -> None:
    """schedules.cron_job_id 컬럼을 제거한다.

    입력: 없음
    출력: 없음
    기능: 외부 cron 연동 컬럼만 되돌린다.
    """
    with op.batch_alter_table("schedules") as batch:
        batch.drop_column("cron_job_id")
