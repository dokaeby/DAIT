"""예약 검색 실행 이력과 검색 결과 테이블을 만든다 (예약 검색·카카오 연동 업무).

Revision ID: 0004_schedule_runs
Revises: 0003_news_settings
Create Date: 2026-11-11
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_schedule_runs"
down_revision = "0003_news_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """schedule_runs(회차별 실행 이력)와 schedule_run_items(검색 결과)를 만든다.

    입력: 없음
    출력: 없음
    기능: 한 예약의 같은 회차는 dedupe_key UNIQUE로 한 번만 생기게 하고,
          검색 단계와 카카오 전송 단계의 상태·시도 횟수·실패 이유를 따로 기록한다.
          예약을 지워도 사용자가 받은 결과는 남도록 schedule_id는 SET NULL로 둔다.
    """
    op.create_table(
        "schedule_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("dedupe_key", sa.String(200), nullable=False, unique=True),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=False),
        sa.Column("criteria_json", sa.Text(), nullable=False),
        sa.Column("search_status", sa.String(20), nullable=False),
        sa.Column("search_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("search_error", sa.String(200), nullable=True),
        sa.Column("result_count", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notify_status", sa.String(20), nullable=False),
        sa.Column("notify_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notify_error", sa.String(200), nullable=True),
        sa.Column("notify_next_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schedule_runs_user_created", "schedule_runs", ["user_id", "created_at"])
    op.create_index("ix_schedule_runs_search_status", "schedule_runs", ["search_status"])
    op.create_index("ix_schedule_runs_notify_status", "schedule_runs", ["notify_status"])

    op.create_table(
        "schedule_run_items",
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("schedule_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("news_id", sa.String(36), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_lines", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("run_id", "position", name="pk_schedule_run_items"),
    )


def downgrade() -> None:
    """만든 테이블을 자식부터 지운다.

    입력: 없음
    출력: 없음
    기능: 외래키 순서를 지킨다.
    """
    op.drop_table("schedule_run_items")
    op.drop_index("ix_schedule_runs_notify_status", table_name="schedule_runs")
    op.drop_index("ix_schedule_runs_search_status", table_name="schedule_runs")
    op.drop_index("ix_schedule_runs_user_created", table_name="schedule_runs")
    op.drop_table("schedule_runs")
