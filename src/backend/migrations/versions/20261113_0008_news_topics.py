"""기사 주제 분류 결과(news_topics)와 분류 상태(news_classified) 테이블을 만든다.

Revision ID: 0008_news_topics
Revises: 0007_merge_schedule_onboarding
Create Date: 2026-11-13
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_news_topics"
down_revision = "0007_merge_schedule_onboarding"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """분류 결과 테이블 두 개를 만든다(SQLite·PostgreSQL 공통 문법만 사용).

    입력: 없음
    출력: 없음
    기능: news_classified는 기사별 마지막 분류 시점의 content_updated_at을
          기록해 변경분만 재분류하고, news_topics는 기사-주제 매칭 결과를
          정규화해 저장한다. 관심사·주제 조회가 LIKE 전문 검색 대신
          이 저장 결과를 읽게 한다.
    """
    op.create_table(
        "news_classified",
        sa.Column(
            "news_id",
            sa.String(36),
            sa.ForeignKey("news.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("content_updated_at", sa.String(64), nullable=False),
        sa.Column("classified_at", sa.String(64), nullable=False),
    )
    op.create_table(
        "news_topics",
        sa.Column(
            "news_id",
            sa.String(36),
            sa.ForeignKey("news.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic_code", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("news_id", "topic_code", name="pk_news_topics"),
    )
    op.create_index("ix_news_topics_code", "news_topics", ["topic_code"])


def downgrade() -> None:
    """분류 테이블을 자식부터 지운다."""
    op.drop_index("ix_news_topics_code", table_name="news_topics")
    op.drop_table("news_topics")
    op.drop_table("news_classified")
