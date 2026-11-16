"""소셜 연결(0008_social_identities)과 뉴스 주제(0008_news_topics) 두 갈래를 하나로 합친다.

Revision ID: 0009_merge_social_topics
Revises: 0008_news_topics, 0008_social_identities
Create Date: 2026-11-13
"""

revision = "0009_merge_social_topics"
down_revision = ("0008_news_topics", "0008_social_identities")
branch_labels = None
depends_on = None


# 입력: 두 갈래가 모두 적용될 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 테이블을 바꾸지 않고 이력만 한 줄로 합친다.
def upgrade() -> None:
    """두 마이그레이션 이력을 합친다.

    입력: 없음
    출력: 없음
    기능: 이미 한쪽만 적용된 DB는 나머지 갈래를 적용한 뒤 이 합침 지점으로 올라온다.
    """


# 입력: 합침 지점까지 적용된 Alembic DB 상태.
# 출력: 반환값 없음.
# 동작: 합침만 되돌려 두 갈래를 다시 독립된 head로 둔다.
def downgrade() -> None:
    """합침만 되돌린다(테이블은 그대로).

    입력: 없음
    출력: 없음
    기능: 각 갈래의 downgrade는 따로 실행한다.
    """
