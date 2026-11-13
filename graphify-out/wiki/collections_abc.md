# collections_abc

> 23 nodes

## Key Concepts

- **collections_abc** (47 connections)
- **content_extractor.py** (19 connections) — `src/backend/app/collectors/content_extractor.py`
- **url_safety.py** (17 connections) — `src/backend/src/dait/core/url_safety.py`
- **fetch_article_body_with_trafilatura()** (15 connections) — `src/backend/app/collectors/content_extractor.py`
- **socket** (12 connections)
- **is_public_ip()** (6 connections) — `src/backend/app/collectors/content_extractor.py`
- **_validate_public_url()** (4 connections) — `src/backend/app/collectors/content_extractor.py`
- **test_trafilatura_extracts_clean_body_and_blocks_ssrf_private_ip()** (4 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **ipaddress** (3 connections)
- **resolve_public_host()** (2 connections) — `src/backend/app/collectors/content_extractor.py`
- **_default_resolver()** (2 connections) — `src/backend/src/dait/core/url_safety.py`
- **HttpUrl** (2 connections)
- **private_dns()** (1 connections) — `tests/backend/tests/unit/test_ai_processor.py`
- **AsyncBaseTransport** (1 connections)
- **Resolver** (1 connections)
- **SSRF-safe article HTML fetcher and Trafilatura pure-body text extractor.** (1 connections) — `src/backend/app/collectors/content_extractor.py`
- **Resolve hostname via OS DNS and return all socket addresses.** (1 connections) — `src/backend/app/collectors/content_extractor.py`
- **Reject loopback, private, link-local, multicast, and cloud metadata IPs (SSRF…** (1 connections) — `src/backend/app/collectors/content_extractor.py`
- **Fetch an article detail page with strict SSRF protection and extract body via…** (1 connections) — `src/backend/app/collectors/content_extractor.py`
- **SSRF 방어: 외부 URL이 공인 HTTPS 주소인지 확인하고 안전하게 가져온다 (FR-PIPE-01). 모든 외부 요청 전에 이 모듈의…** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **호스트명에 연결되는 IP 문자열 목록을 돌려준다(socket.getaddrinfo 래퍼).** (1 connections) — `src/backend/src/dait/core/url_safety.py`
- **ambiguous_python_import_cb32e6b4a878** (1 connections)
- **trafilatura** (1 connections)

## Relationships

- [ai_processor.py](ai_processor.py.md) (15 shared connections)
- [test_ai_processor.py](test_ai_processor.py.md) (5 shared connections)
- [CollectorSource](CollectorSource.md) (4 shared connections)
- [collection_service.py](collection_service.py.md) (3 shared connections)
- [robots_service.py](robots_service.py.md) (3 shared connections)
- [validate_public_https_url](validate_public_https_url.md) (3 shared connections)
- [test_app_news_api.py](test_app_news_api.py.md) (3 shared connections)
- [CollectionResult](CollectionResult.md) (2 shared connections)
- [db_search.py](db_search.py.md) (2 shared connections)
- [ui/conftest.py](ui-conftest.py.md) (2 shared connections)
- [db_postgres.py](db_postgres.py.md) (2 shared connections)
- [test_news_repository.py](test_news_repository.py.md) (2 shared connections)

## Source Files

- `src/backend/app/collectors/content_extractor.py`
- `src/backend/src/dait/core/url_safety.py`
- `tests/backend/tests/unit/test_ai_processor.py`

## Audit Trail

- EXTRACTED: 112 (97%)
- INFERRED: 3 (3%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*