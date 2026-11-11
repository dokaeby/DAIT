# 5단계: 국내 기사 3~5개 AI 요약 품질 테스트

이 단계는 기사 전문이 아닌 기존 DB의 RSS 설명을 입력으로 사용합니다. 짧거나 잘린 입력에서 원문 전체 요약을 기대할 수는 없습니다. `generated`는 응답 형식이 정상이라는 뜻이며 내용의 정확성이나 자연스러움을 보장하지 않습니다. `insufficient`는 모델이 세 가지 요점을 만들 정보가 부족하다고 판단한 경우입니다.

## 준비

1. https://ollama.com/download/windows 에서 Ollama를 설치하고 실행합니다. 설치 후 VS Code 터미널을 새로 열어 주세요.
2. 모델을 내려받습니다. 다운로드에는 인터넷 연결과 저장 공간이 필요합니다.

```powershell
ollama pull qwen3:4b
```

기본 모델은 로컬 실행을 위한 테스트 선택입니다. 노트북에서 실제 속도와 품질은 확인이 필요하며, CPU에서 첫 실행과 기사별 생성에 시간이 걸릴 수 있습니다. Python은 기존 단계와 동일하며 추가 Python 패키지는 없습니다.

## 실행

먼저 네트워크 요청 없이 대상 국내 기사와 RSS 설명을 확인합니다.

```powershell
py ui_step3\test_summaries.py --list
```

이후 3개 기사를 순차적으로 요약합니다. 메인화면 서버를 실행할 필요는 없습니다.

```powershell
py ui_step3\test_summaries.py
```

5개를 확인하거나 대기 시간을 조정할 수도 있습니다.

```powershell
py ui_step3\test_summaries.py --count 5 --timeout 900
```

기본 기사별 제한 시간은 600초입니다. 호출 주소는 로컬 `127.0.0.1:11434`이며 입력 기사 데이터는 이 로컬 API로 전달됩니다. 실행 도중 중단하려면 Ctrl+C를 누릅니다. 완료된 기사별 결과는 DB에 저장됩니다.

## 결과와 확인 방법

- `ui_step3/summary_tests.db`: 실행별 입력, 모델명, 요약, 상태, 소요 시간, 오류를 저장합니다. 기존 기사 DB는 읽기만 합니다. `reviewed=0`은 아직 사람이 검토 완료한 결과가 아니라는 뜻입니다.
- `ui_step3/summary_report_실행ID.txt`: 입력과 AI 결과를 비교하는 UTF-8 보고서입니다. VS Code에서 열어 확인하세요.

각 결과에서 세 문장이 서로 다른 핵심 사실인지, 이름·수치·날짜가 맞는지, 잘린 문장을 추측해 채우지 않았는지 확인하세요. `insufficient`도 정상적인 테스트 결과이므로 억지로 세 줄을 채우지 않습니다. 같은 명령을 다시 실행하면 별도 실행 기록이 생깁니다. 현재 팝업 연결 방법은 `README_요약연결.md`, 국내 기사 전체 처리 방법은 `README_국내전체요약.md`를 참고하세요.

연결 오류는 Ollama가 실행 중인지 확인하세요. 모델을 찾지 못하면 `ollama list`로 확인하고 위 pull 명령을 실행하세요. 형식 오류나 시간 초과도 결과 보고서에 기록됩니다.

공식 참고: [Windows 설치 및 실행](https://docs.ollama.com/windows), [생성 API](https://docs.ollama.com/api/generate), [구조화된 응답](https://docs.ollama.com/capabilities/structured-outputs), [모델](https://ollama.com/library/qwen3:4b).
