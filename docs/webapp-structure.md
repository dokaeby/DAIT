# DAIT 웹앱 폴더 구조

Python/FastAPI 서버와 HTML·CSS·JavaScript 화면을 분리한다. Supabase는 데이터 저장과 로그인/SNS 인증을 담당하고, Redis는 캐시와 만료되는 임시 데이터를 담당한다. 웹 검색은 앱에서 제공할 기능이다.

현재는 폴더 구조만 준비한 상태다. 실행 코드, 패키지 설치, 외부 서비스 연결은 아직 포함하지 않는다.

```text
DAIT/
├─ src/
│  ├─ frontend/
│  │  ├─ templates/                  # HTML 화면
│  │  └─ static/
│  │     ├─ css/                     # 스타일
│  │     └─ js/                      # 화면 동작과 API 호출
│  └─ backend/
│     └─ app/
│        ├─ api/                     # FastAPI 라우터: 인증·사용자·검색
│        ├─ core/                    # 환경 설정과 인증 토큰 검증
│        ├─ schemas/                 # 요청·응답 검증 모델
│        ├─ services/
│        │  ├─ auth/                 # 로그인·로그아웃·SNS 로그인 흐름
│        │  └─ search/               # 웹 검색 로직과 결과 정리
│        └─ integrations/
│           ├─ supabase/             # Supabase DB/Auth 연결
│           └─ redis/                # Redis 연결과 캐시 접근
├─ tests/
│  ├─ backend/                      # API·인증·검색 테스트
│  └─ frontend/                     # 화면 동작 테스트
├─ config/                          # 공유 설정 예시
└─ docs/                            # 기존 기획서와 개발 문서
```

## 기능별 역할

| 기능 | 담당 위치 | 구현 방향 |
| --- | --- | --- |
| 화면 | `src/frontend/templates`, `static` | HTML·CSS·JavaScript로 구성 |
| API | `src/backend/app/api` | FastAPI 엔드포인트 정의 |
| 로그인 인증 | `services/auth`, `core`, `integrations/supabase` | Supabase Auth가 발급한 토큰을 서버에서 검증 |
| SNS 로그인 | `services/auth`, `integrations/supabase` | Supabase Auth의 OAuth 제공자 사용. 제공자는 추후 선택 |
| 데이터 저장 | `integrations/supabase` | 사용자별 데이터 접근 정책(RLS) 적용 |
| Redis | `integrations/redis` | 검색 결과 캐시 등 만료 가능한 데이터 저장. 인증의 기준은 Supabase Auth |
| 웹 검색 | `services/search`, `api` | 검색 제공자 API 연동과 입력·결과 검증. 제공자는 추후 선택 |

인증 비밀키와 검색 API 키는 환경 변수로 관리한다. Supabase의 서버 전용 비밀키는 프론트엔드에 전달하지 않는다. Redis에도 비밀번호나 장기 인증 토큰을 저장하지 않는다.

실제 구현 시에는 FastAPI 진입점, Python 의존성 파일과 환경 변수 예시를 추가한다. SNS 제공자와 웹 검색 제공자를 선택한 뒤 콜백 주소, API 키, 사용 한도를 설정한다.

각 빈 폴더의 `.gitkeep`은 Git 추적용이며 실행 파일이 아니다.
