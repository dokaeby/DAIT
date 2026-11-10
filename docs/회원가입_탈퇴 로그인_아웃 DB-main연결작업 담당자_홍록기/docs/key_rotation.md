# 서명 키(JWT_SECRET) 교체 절차

access 토큰은 `JWT_SECRET`으로 서명한다. refresh 토큰은 서명이 아니라 무작위 문자열(DB에는 해시만 저장)이라
키를 바꿔도 refresh 토큰은 그대로 유효하다.

## 정기 교체 또는 유출이 의심될 때

1. 새 키를 만든다: `python -c "import secrets; print(secrets.token_urlsafe(48))"` (32자 이상).
2. 배포 환경의 `JWT_SECRET`을 새 값으로 바꾸고 서버를 다시 시작한다. 코드·Git·이미지·로그에는 넣지 않는다.
3. 영향: 기존 access 토큰(최대 `ACCESS_TOKEN_MINUTES`분)은 즉시 무효가 된다. 사용자는 refresh 토큰으로
   새 access 토큰을 받는다(refresh 기능은 모듈 3에서 구현. 그 전에는 다시 로그인).
4. 유출이 확정이면 추가로 `refresh_tokens` 테이블을 비워 모든 사용자를 다시 로그인시킨다.
   (모듈 3의 "전체 무효화" 기능이 생기면 그 기능을 쓴다.)
5. 이전 키는 폐기하고 교체 시각을 팀 채널에 남긴다.

## 한계

키를 두 개 동시에 허용하는 무중단 교체는 지원하지 않는다. 필요해지면 그때 추가한다.
