# CloudLLMSettings

> 21 nodes

## Key Concepts

- **CloudLLMSettings** (19 connections) — `src/backend/app/workers/cloud_llm.py`
- **.from_env()** (7 connections) — `src/backend/app/workers/cloud_llm.py`
- **LLMClient** (5 connections) — `src/backend/app/workers/cloud_llm.py`
- **cloud_llm_processor_from_env()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **.__init__()** (4 connections) — `src/backend/app/workers/cloud_llm.py`
- **test_from_env_reads_keys()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **test_from_env_returns_none_without_keys()** (4 connections) — `tests/backend/tests/unit/test_cloud_llm.py`
- **.__init__()** (3 connections) — `src/backend/app/workers/cloud_llm.py`
- **Self** (3 connections)
- **.grok_enabled()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **.groq_enabled()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **.complete()** (2 connections) — `src/backend/app/workers/cloud_llm.py`
- **MonkeyPatch** (2 connections)
- **Protocol** (1 connections)
- **XAI_API_KEY가 실질적으로 설정된 경우에만 xAI 호출을 허용한다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **환경변수에 LLM 키가 있으면 클라우드 프로세서를, 없으면 None을 yield한다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **GROQ_API_KEY가 실질적으로 설정된 경우에만 Groq 호출을 허용한다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **환경변수로부터 설정을 만들고, 키가 없으면 None을 반환한다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **LLM 호출 경계. 어댑터는 시스템 지시와 사용자 프롬프트를 분리해 전달한다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **JSON 문자열을 반환한다. 도구·URL 호출은 허용하지 않는다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`
- **클라우드 LLM 프로바이더 설정. 자격증명은 SecretStr로 감싼다.** (1 connections) — `src/backend/app/workers/cloud_llm.py`

## Relationships

- [test_cloud_llm.py](test_cloud_llm.py.md) (8 shared connections)
- [GrokClient](GrokClient.md) (6 shared connections)
- [ai_processor.py](ai_processor.py.md) (4 shared connections)
- [CloudSummaryProcessor](CloudSummaryProcessor.md) (2 shared connections)
- [GrokSummaryCompletion](GrokSummaryCompletion.md) (1 shared connections)
- [_ManagedRuntime](_ManagedRuntime.md) (1 shared connections)
- [test_taxonomy_and_categories.py](test_taxonomy_and_categories.py.md) (1 shared connections)

## Source Files

- `src/backend/app/workers/cloud_llm.py`
- `tests/backend/tests/unit/test_cloud_llm.py`

## Audit Trail

- EXTRACTED: 42 (91%)
- INFERRED: 4 (9%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*