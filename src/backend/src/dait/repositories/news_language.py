"""Use the same source-aware language expression in lists and interest counts."""

NEWS_LANGUAGE_SQL = """CASE
    WHEN s.name IN ('MIT Tech Review', 'TechCrunch', 'The Verge') THEN 'en'
    WHEN lower(n.original_language) LIKE 'en%' THEN 'en'
    WHEN lower(n.original_language) LIKE 'ko%' THEN 'ko'
    WHEN n.original_language = 'und' AND s.name IN
        ('AI타임스', 'IT조선', '뉴시스', '디지털데일리', '디지털투데이', '매일경제',
         '바이라인네트워크', '블로터', '서울경제', '연합뉴스', '전자신문', '지디넷코리아',
         '테크M', '한국경제') THEN 'ko'
    ELSE n.original_language END"""
