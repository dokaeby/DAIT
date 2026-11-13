# backend/src/dait/schemas/interest.py

> 25 nodes

## Key Concepts

- **backend/src/dait/schemas/interest.py** (12 connections) — `src/backend/src/dait/schemas/interest.py`
- **InterestCode** (6 connections) — `src/backend/src/dait/schemas/interest.py`
- **._no_duplicates()** (5 connections) — `src/backend/src/dait/schemas/interest.py`
- **BaseModel** (5 connections)
- **InterestItem** (4 connections) — `src/backend/src/dait/schemas/interest.py`
- **InterestsUpdateRequest** (4 connections) — `src/backend/src/dait/schemas/interest.py`
- **check_no_duplicates()** (4 connections) — `src/backend/src/dait/schemas/interest.py`
- **CatalogResponse** (3 connections) — `src/backend/src/dait/schemas/interest.py`
- **InterestGroup** (3 connections) — `src/backend/src/dait/schemas/interest.py`
- **MyInterestsResponse** (3 connections) — `src/backend/src/dait/schemas/interest.py`
- **empty_interests()** (3 connections) — `src/backend/src/dait/schemas/interest.py`
- **empty_items()** (3 connections) — `src/backend/src/dait/schemas/interest.py`
- **field_validator** (1 connections)
- **StrEnum** (1 connections)
- **관심사 코드(15개)와 카탈로그·요청·응답 모델. 코드 철자는 README 6.2절 표로 고정한다.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **선택 가능한 관심사 전체를 대주제별로 묶은 응답.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **내 관심사 응답. 카탈로그 순서로 정렬되어 나간다.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **선택할 수 있는 관심사 소주제. `대주제.소주제` 형식의 영문 고정 코드다.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **내 관심사 전체 교체 요청. 빈 목록은 선택 해제다.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **중복 코드를 거부한다. 입력: value (코드 목록) 출력: 같은 목록 기능: check_no_duplicates에 맡긴다.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **화면에 보여 줄 관심사 한 개: 저장 코드, 한글 이름, 대주제.** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **빈 관심사 목록을 만든다. 입력: 없음 출력: list[InterestCode] (새 빈 목록) 기능: 필드 기본값 공장으로 써서…** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **빈 관심사 항목 목록을 만든다. 입력: 없음 출력: list[InterestItem] (새 빈 목록) 기능: 응답 모델의 기본값 공장으로 써서…** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **관심사 목록에 같은 코드가 두 번 들어 있지 않은지 확인한다. 입력: values (이미 Enum 검증을 통과한 코드 목록) 출력: 같은 목록…** (1 connections) — `src/backend/src/dait/schemas/interest.py`
- **대주제 한 개와 그 아래 소주제들(대주제를 누르면 소주제가 보이는 화면용).** (1 connections) — `src/backend/src/dait/schemas/interest.py`

## Relationships

- [enum](enum.md) (1 shared connections)
- [ai_processor.py](ai_processor.py.md) (1 shared connections)

## Source Files

- `src/backend/src/dait/schemas/interest.py`

## Audit Trail

- EXTRACTED: 35 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*