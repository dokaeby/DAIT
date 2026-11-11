<<<<<<< HEAD
# DAIT 화면·데이터 연동 테스트

현재 진행 상태와 다음 작업은 **[HANDOFF.md](HANDOFF.md)** 를 먼저 읽어 주세요. 기준 시점은 2026-11-09(한국 시간)입니다.

## 다른 PC에서 시작

Python 3.10 이상을 설치한 Windows PC의 프로젝트 폴더에서 가상환경을 새로 만듭니다. 기존 `.venv`는 복사하지 않습니다.

```cmd
py -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r ui_step4\requirements.txt
python ui_step2\app.py
```

## 화면에서 확인

- 뉴스 메인 및 상세 팝업: http://127.0.0.1:8000/
- 임베딩 유사도 비교: http://127.0.0.1:8000/search-lab

기능 테스트는 브라우저에서 합니다. 유사도 화면에서 **색인 준비·갱신 → 유사도 비교** 순서로 진행합니다. 최초 모델 다운로드에 인터넷 연결이 필요합니다.

메인화면의 테스트 계정은 user1(인공지능), user2(보안·클라우드), user3(반도체)입니다. 실제 인증 서비스가 아닙니다. 현재 메인 검색은 키워드 방식이며 임베딩 비교는 별도 화면입니다.

## 업로드에 포함할 파일

소스·HTML·문서·`ui_step4/requirements.txt`와 현재 생성된 프로젝트 DB를 함께 올려야 같은 데이터에서 이어갈 수 있습니다. `.gitignore`에 네 가지 프로젝트 DB의 예외를 등록했습니다. `.venv`, 모델 캐시, 보고서 `.txt`는 기본 제외입니다.

파일을 업로드하기 전 진행 중인 색인·요약 작업이 끝난 것을 확인하고 서버를 종료하세요. GitHub 업로드는 사용자가 수행합니다.
=======
# search_test
검색 기능 테스트용
>>>>>>> origin/main
