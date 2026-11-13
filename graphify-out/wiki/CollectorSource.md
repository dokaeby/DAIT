# CollectorSource

> 38 nodes

## Key Concepts

- **CollectorSource** (43 connections) — `src/backend/app/schemas/collector.py`
- **rss_collector.py** (41 connections) — `src/backend/app/collectors/rss_collector.py`
- **_parse()** (13 connections) — `src/backend/app/collectors/rss_collector.py`
- **.collect()** (8 connections) — `src/backend/app/collectors/rss_collector.py`
- **._download()** (8 connections) — `src/backend/app/collectors/rss_collector.py`
- **_validate_url()** (8 connections) — `src/backend/app/collectors/rss_collector.py`
- **_TextExtractor** (7 connections) — `src/backend/app/collectors/rss_collector.py`
- **_extract_article_url()** (7 connections) — `src/backend/app/collectors/rss_collector.py`
- **._robots()** (7 connections) — `src/backend/app/collectors/rss_collector.py`
- **.__init__()** (6 connections) — `src/backend/app/collectors/rss_collector.py`
- **_extract_body_text()** (5 connections) — `src/backend/app/collectors/rss_collector.py`
- **_public_ip()** (5 connections) — `src/backend/app/collectors/rss_collector.py`
- **HttpUrl** (5 connections)
- **_is_article_detail_url()** (4 connections) — `src/backend/app/collectors/rss_collector.py`
- **_parse_pub_date()** (4 connections) — `src/backend/app/collectors/rss_collector.py`
- **_text()** (4 connections) — `src/backend/app/collectors/rss_collector.py`
- **_child_text()** (3 connections) — `src/backend/app/collectors/rss_collector.py`
- **_robots_allowed()** (2 connections) — `src/backend/app/collectors/rss_collector.py`
- **.__init__()** (2 connections) — `src/backend/app/collectors/rss_collector.py`
- **datetime** (2 connections)
- **email_utils** (2 connections)
- **html_parser** (2 connections)
- **_Messages** (1 connections) — `src/backend/app/collectors/rss_collector.py`
- **resolve_host()** (1 connections) — `src/backend/app/collectors/rss_collector.py`
- **.handle_data()** (1 connections) — `src/backend/app/collectors/rss_collector.py`
- *... and 13 more nodes in this community*

## Relationships

- [unit/test_collector.py](unit-test_collector.py.md) (19 shared connections)
- [ai_processor.py](ai_processor.py.md) (16 shared connections)
- [CollectionResult](CollectionResult.md) (11 shared connections)
- [test_pipeline_flow.py](test_pipeline_flow.py.md) (8 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (6 shared connections)
- [test_worker_and_real_ai_processor_use_sqlite_repository](test_worker_and_real_ai_processor_use_sqlite_repository.md) (4 shared connections)
- [collections_abc](collections_abc.md) (4 shared connections)
- [dait/pipelines/collect_news.py](dait-pipelines-collect_news.py.md) (2 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (1 shared connections)
- [NewsListItem](NewsListItem.md) (1 shared connections)
- [db_search.py](db_search.py.md) (1 shared connections)
- [robots_service.py](robots_service.py.md) (1 shared connections)

## Source Files

- `src/backend/app/collectors/rss_collector.py`
- `src/backend/app/schemas/collector.py`

## Audit Trail

- EXTRACTED: 120 (86%)
- INFERRED: 19 (14%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*