# 1단계: 실제 뉴스 수집

프로젝트 폴더에서 다음 명령을 실행하세요. Python 3만 필요하며 별도 패키지 설치는 없습니다.

```powershell
py ui_step1\collect_news.py
```

인터넷 연결이 필요합니다. 전자신문, TechCrunch, The Verge의 공개 RSS에서 중복을 제거하고 발행일 최신순 50개를 `ui_step1/real_articles.db`에 저장합니다. 목록에 포함된 언론사 중 세 곳을 대상으로 합니다. 50개 미만이면 오류를 출력하고 기존 DB를 덮어쓰지 않습니다. 언론사 RSS 제공 상태나 네트워크 차단에 따라 수집에 실패할 수 있습니다.

이미 수집한 JSON을 그대로 DB로 옮기려면 인터넷 접속 없이 다음 명령을 실행하세요.

```powershell
py ui_step1\collect_news.py --from-json ui_step1\real_articles.json
```

DB에는 기사 정보를 담는 `articles` 테이블과 기사별 관심 분야를 담는 `article_categories` 테이블이 있습니다. `article_categories.article_id`가 `articles.id`를 참조하며, 기사 하나에 여러 카테고리가 연결될 수 있습니다. 재실행하면 이 DB의 기사 50개가 새 결과로 교체됩니다. 기존 JSON은 수정하지 않습니다. DB Browser for SQLite 등의 도구에서 열어 내용을 확인할 수 있습니다.

각 기사의 `original_url`은 원문 링크입니다. `content`와 `summary`는 RSS에서 제공하는 설명이며 기사 전문이나 별도로 생성한 요약이 아닙니다. 설명이 없는 경우 비어 있을 수 있습니다. 카테고리는 제목과 설명에 포함된 키워드로 추정하므로 부정확하거나 `기타`일 수 있습니다. 출력된 카테고리별 건수를 확인하세요. 발행 시각은 UTC입니다.

수집 또는 변환 후 DB와 터미널의 출력 내용을 확인해 주세요. 이후 화면 구현 단계에서 이 데이터와 사용자 관심사를 연결할 수 있습니다.

DB의 기사 수와 출처, 최신 10개를 확인하려면 다음 명령을 실행하세요. DB는 읽기만 합니다.

```powershell
py ui_step1\check_news.py
```

검사는 링크의 출처 도메인과 필수 필드, 중복 여부를 확인합니다. 각 기사 원문이 실제로 열리는지와 표시·이용 조건을 확인하는 검사는 아닙니다. 출력 결과를 확인한 후 다음 단계로 진행하세요.
