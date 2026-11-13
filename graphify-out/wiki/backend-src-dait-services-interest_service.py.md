# backend/src/dait/services/interest_service.py

> 25 nodes

## Key Concepts

- **backend/src/dait/services/interest_service.py** (12 connections) — `src/backend/src/dait/services/interest_service.py`
- **replace_my_interests()** (7 connections) — `src/backend/src/dait/services/interest_service.py`
- **get_my_interests()** (6 connections) — `src/backend/src/dait/services/interest_service.py`
- **_item()** (6 connections) — `src/backend/src/dait/services/interest_service.py`
- **list_interests()** (6 connections) — `src/backend/src/dait/services/interest_service.py`
- **_to_response()** (6 connections) — `src/backend/src/dait/services/interest_service.py`
- **get_catalog()** (4 connections) — `src/backend/src/dait/services/interest_service.py`
- **MyInterestsResponse** (4 connections)
- **Settings** (3 connections)
- **InterestCode** (2 connections)
- **UserRecord** (2 connections)
- **CatalogResponse** (1 connections)
- **InterestItem** (1 connections)
- **관심사 카탈로그 구성과 내 관심사 조회·교체 규칙을 처리한다.** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **코드 하나를 화면용 항목으로 바꾼다. 입력: code (관심사 코드) 출력: InterestItem (코드, 한글 이름, 대주제) 기능:…** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **선택 가능한 관심사 전체를 대주제별로 묶어 돌려준다. 입력: 없음 출력: CatalogResponse (대주제 3개, 소주제 15개) 기능:…** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **저장된 코드 문자열을 카탈로그 순서의 응답으로 바꾼다. 입력: codes (DB에서 읽은 코드 문자열) 출력:…** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **사용자 id로 저장된 관심사를 읽는다(로그인 응답에 붙이는 용도). 입력: settings (앱 설정), user_id (인증이 끝난 사용자의…** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **본인의 관심사를 돌려준다. 입력: settings (앱 설정), user (토큰으로 확인된 본인) 출력: MyInterestsResponse…** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **본인의 관심사를 주어진 목록으로 통째로 바꾼다. 입력: settings (앱 설정), user (본인), codes (중복 없고 15개 이하인…** (1 connections) — `src/backend/src/dait/services/interest_service.py`
- **ambiguous_python_import_0bc62dd23c20** (1 connections)
- **ambiguous_python_import_495f23899f4c** (1 connections)
- **ambiguous_python_import_ba7e327f93ac** (1 connections)
- **ambiguous_python_import_f7a2014adf7d** (1 connections)
- **ambiguous_python_import_fc08ae1607f8** (1 connections)

## Relationships

- No strong cross-community connections detected

## Source Files

- `src/backend/src/dait/services/interest_service.py`

## Audit Trail

- EXTRACTED: 36 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*