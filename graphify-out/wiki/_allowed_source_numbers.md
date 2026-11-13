# _allowed_source_numbers

> 12 nodes

## Key Concepts

- **_allowed_source_numbers()** (6 connections) — `src/backend/app/workers/cloud_llm.py`
- **_numbers_within_source()** (6 connections) — `src/backend/app/workers/cloud_llm.py`
- **_extract_korean_scales()** (5 connections) — `src/backend/app/workers/cloud_llm.py`
- **_english_number_values()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **_num_key()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **flush()** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **repl()** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **Canonical (number, is_percent) key — 표기 차이를 흡수한다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **Expand spelled-out English numbers; returns (values, percent-context values).** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **Canonical numeric keys allowed in output: literal digits plus spelled-out…** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **Strip Korean scale numerals (48만4천, 3만7000) and return (cleaned_text, values).** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **Reject outputs whose numeric tokens never appear in the source.** (1 connections) — `src/backend/app/workers/cloud_llm.py`

## Relationships

- [ai_processor.py](ai_processor.py.md) (5 shared connections)
- [CloudSummaryProcessor](CloudSummaryProcessor.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/cloud_llm.py`

## Audit Trail

- EXTRACTED: 18 (95%)
- INFERRED: 1 (5%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*