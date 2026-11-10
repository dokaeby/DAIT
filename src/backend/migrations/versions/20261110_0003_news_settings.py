"""뉴스·설정·작업·알림·감사 테이블을 만든다 (DB 설계서 3.4~3.13).

Revision ID: 0003_news_settings
Revises: 0002_interests
Create Date: 2026-11-10
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_news_settings"
down_revision = "0002_interests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """설계서의 테이블을 만든다(SQLite·PostgreSQL 공통 문법만 사용).

    입력: 없음
    출력: 없음
    기능: JSON 계열은 TEXT로 저장하고, 목록·소유권·중복 방지에 필요한
          unique/index/check 제약을 함께 건다.
    """
    op.create_table(
        "sources",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=False, unique=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("robots_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_sources_enabled_priority", "sources", ["enabled", "priority"])

    op.create_table(
        "news",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "source_id",
            sa.String(36),
            sa.ForeignKey("sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False, unique=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("original_language", sa.String(8), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_news_title", "news", ["title"])
    op.create_index("ix_news_published_at", "news", ["published_at"])
    op.create_index("ix_news_category_published", "news", ["category", "published_at"])
    op.create_index("ix_news_content_hash", "news", ["content_hash"])

    op.create_table(
        "content_results",
        sa.Column(
            "news_id",
            sa.String(36),
            sa.ForeignKey("news.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("translated_text", sa.Text(), nullable=True),
        sa.Column("summary_lines", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("prompt_version", sa.String(40), nullable=True),
        sa.Column("model_id", sa.String(80), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_content_results_status", "content_results", ["status"])

    op.create_table(
        "news_relations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "news_id",
            sa.String(36),
            sa.ForeignKey("news.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_news_id",
            sa.String(36),
            sa.ForeignKey("news.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("news_id", "related_news_id", name="uq_news_relations_pair"),
        sa.CheckConstraint("news_id <> related_news_id", name="ck_news_relations_not_self"),
    )
    op.create_index("ix_news_relations_news_score", "news_relations", ["news_id", "score"])

    op.create_table(
        "user_settings",
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("default_count", sa.SmallInteger(), nullable=False, server_default="10"),
        sa.Column("categories", sa.Text(), nullable=False, server_default='["AI"]'),
        sa.Column("keywords", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("source_ids", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("in_app_notice", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("email_notice", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("default_count IN (5, 10)", name="ck_user_settings_count"),
    )

    op.create_table(
        "schedules",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("local_time", sa.String(8), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criteria_json", sa.Text(), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_schedules_user_id", "schedules", ["user_id"])
    op.create_index("ix_schedules_due", "schedules", ["enabled", "next_run_at"])

    op.create_table(
        "jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("schedules.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_status_scheduled", "jobs", ["status", "scheduled_at"])

    op.create_table(
        "job_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "job_id",
            sa.String(36),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step", sa.String(20), nullable=False),
        sa.Column("attempt_no", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("job_id", "step", "attempt_no", name="uq_job_attempts_step"),
    )

    op.create_table(
        "notification_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "schedule_id",
            sa.String(36),
            sa.ForeignKey("schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "news_id",
            sa.String(36),
            sa.ForeignKey("news.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("channel", sa.String(10), nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False, unique=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_notification_deliveries_status", "notification_deliveries", ["status"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "actor_user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event", sa.String(40), nullable=False),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", sa.String(64), nullable=True),
        sa.Column("request_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_event", "audit_logs", ["event"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    """만든 테이블을 외래키 역순으로 지운다.

    입력: 없음
    출력: 없음
    기능: 자식 테이블부터 지워 참조 순서를 지킨다.
    """
    for table in (
        "audit_logs",
        "notification_deliveries",
        "job_attempts",
        "jobs",
        "schedules",
        "user_settings",
        "news_relations",
        "content_results",
        "news",
        "sources",
    ):
        op.drop_table(table)
