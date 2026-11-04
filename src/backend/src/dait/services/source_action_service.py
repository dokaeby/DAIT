"""FR-DETAIL-02 원문 열기·링크 복사 데이터 구현 가이드.

담당 기능: 검증된 원문 URL과 공유 가능한 canonical URL을 제공한다.
구현 로직: 기사 조회 → 저장 URL 재검증 → 허용된 HTTPS URL 정규화 → 동작 메타 반환 순으로 처리한다.
보안·검증: SSRF 방어, scheme·host 허용 목록, 사용자 제공 redirect 금지, 추적 파라미터 제거를 적용한다.
테스트: 정상 HTTPS, 금지 host, 사설 IP, 잘못된 scheme, 없는 기사를 검증한다.
실제 URL 처리는 소스 정책 승인 후 구현한다.
"""
