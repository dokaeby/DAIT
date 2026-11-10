"""화면설계서 v1.0.3의 메인·상세 구조와 실제 데이터 표시."""
import json
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote, urlencode, urlsplit


def safe_url(raw):
    parts = urlsplit(raw or "")
    return raw if parts.scheme in ("https", "http") and parts.netloc else None


def summary_status(summary):
    return {"queued": ("pending", "○ 요약 대기 중"), "running": ("pending", "◌ 요약 생성 중"),
            "retry": ("pending", "↻ 재시도 대기"), "failed": ("partial", "! 재시도 종료"),
            "generated": ("ready", "✓ 요약 생성 · 검토 전"), "insufficient": ("partial", "△ 정보 부족"),
            "error": ("partial", "! 생성 실패"), "stale": ("partial", "↻ 갱신 필요"),
            "invalid": ("partial", "! 형식 확인"), "unavailable": ("partial", "! 조회 불가")}.get(summary.get("status"), ("pending", "○ 요약 준비 전"))


def shell(content, user=None, query="", active="home", dialogs="", script=False, category="", inbox_unseen=0):
    status = f"{escape(user)} 로그인 중" if user else "비로그인"
    logout = '<form method="post" action="/logout"><button class="secondary-button" type="submit">로그아웃</button></form>' if user else ""
    user_button = '<button class="primary-button" type="button" id="login-open">' + ("계정 전환" if user else "로그인") + '</button>' if script else '<a class="primary-button" href="/">메인으로</a>'
    settings_button = '<a class="text-button settings-link" href="/settings"' + (' aria-current="page"' if active == 'settings' else '') + '>설정</a>' if user else ''
    settings_nav = '<nav class="nav-group"><span class="nav-label">Workspace</span><a class="nav-item ' + ('active' if active == 'settings' else '') + '" href="/settings">⚙ 설정</a></nav>' if user else ''
    settings_tab = '<a class="mobile-tab ' + ('active' if active == 'settings' else '') + '" href="/settings">⚙<span>설정</span></a>' if user else ''
    interests_nav = ('<a class="nav-item ' + ('active' if active == 'interests' else '') + '" href="/interests">☆ 관심 카테고리</a>') if user else '<span class="nav-item muted">☆ 관심 뉴스 <small>로그인 후</small></span>'
    categories = '<a class="nav-item ' + ('active' if category else '') + '" href="/?category=' + quote('인공지능') + '">✦ AI·기술</a>'
    badge = f'<small class="inbox-badge" aria-label="새 소식 {inbox_unseen}개">새 {inbox_unseen}</small>' if inbox_unseen else ''
    inbox_nav = ('<a class="nav-item ' + ('active' if active == 'inbox' else '') + '" href="/inbox" id="inbox-nav">🔔 예약 소식함' + badge + '</a>') if user else ''
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DAIT · 오늘의 AI 뉴스</title><link rel="stylesheet" href="/assets/design.css"><link rel="stylesheet" href="/assets/app.css"></head><body>
    <div class="app-shell"><header class="app-header"><a class="brand" href="/" aria-label="DAIT 메인"><span class="brand-mark">DAIT</span><span class="brand-divider"></span><span class="brand-copy">AI 뉴스 큐레이션 서비스</span></a><div class="header-actions"><span class="session-status">{status}</span>{user_button}{logout}{settings_button}</div></header>
    <div class="app-body"><aside class="sidebar" aria-label="주요 탐색"><nav class="nav-group"><span class="nav-label">Discover</span><a class="nav-item {'active' if active == 'home' and not category else ''}" href="/">⌂ 오늘의 AI 뉴스</a>{categories}</nav><nav class="nav-group"><span class="nav-label">Library</span>{interests_nav}{inbox_nav}<span class="nav-item muted">♧ 저장한 뉴스 <small>단계 2</small></span></nav>{settings_nav}<p class="nav-note">RSS 기반 뉴스와 AI 요약을 제공합니다.<br>정확한 내용은 원문을 확인해 주세요.</p></aside><main class="main">{content}</main></div></div>
    <nav class="mobile-tabs {'guest-tabs' if not user else ''}" aria-label="모바일 탐색"><a class="mobile-tab {'active' if not category and active == 'home' else ''}" href="/">⌂<span>오늘의 뉴스</span></a><a class="mobile-tab {'active' if category else ''}" href="/?category={quote('인공지능')}">✦<span>AI·기술</span></a>{settings_tab}</nav>{dialogs}{'<script src="/assets/app.js" defer></script>' if script else ''}</body></html>'''


def _json_for_script(data):
    # <script> 안에 넣는 JSON은 </script> 조기 종료를 막기 위해 < 를 이스케이프합니다.
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


WEEKDAY_NAMES = ('월', '화', '수', '목', '금', '토', '일')


def render_settings_entry(user, interests, state, inbox_unseen=0):
    """KAN-10 설정 화면. 저장한 값을 서버에서 읽어 채우고, 저장 시 /api/settings로 보냅니다."""
    settings = state.settings
    schedule = settings.schedule
    data = _json_for_script({"settings": settings.model_dump(mode="json"),
                             "available_categories": state.available_categories,
                             "next_run": state.next_run})
    days = ''.join(f'<button type="button" class="chip day-chip" data-day="{index}" aria-pressed="false">{name}</button>'
                   for index, name in enumerate(WEEKDAY_NAMES))
    sources = ''.join(f'<button type="button" class="chip source-chip" data-source="{value}" aria-pressed="false">{label}</button>'
                      for value, label in (('interests', '관심 카테고리'), ('keywords', '선호 검색어')))
    max_options = ''.join(f'<option value="{n}" {"selected" if schedule.max_items == n else ""}>{n}건</option>' for n in (5, 10, 20))
    count_options = ''.join(f'<option value="{n}" {"selected" if settings.display_count == n else ""}>{n}개</option>' for n in (10, 5))
    interest_text = ' · '.join(interests) if interests else '설정한 관심 카테고리가 없습니다'
    checked = lambda on: 'checked' if on else ''  # noqa: E731
    content = (
        '<div class="page-head"><div><p class="eyebrow">Personal Workspace</p><h1 class="page-title">설정</h1>'
        '<p class="page-description">예약 알림, 선호 검색어, 카테고리 표시 순서와 노출 방식을 관리합니다.</p></div></div>'
        '<div class="settings-layout"><nav class="settings-menu" aria-label="설정 구역">'
        '<a class="active" aria-current="location" href="#schedule">예약 알림</a><a href="#interests">관심 설정</a>'
        '<a href="#display">노출·알림</a><a href="#account">계정·정책</a></nav>'
        '<form id="settings-form" class="settings-sections" novalidate>'
        # 예약 알림
        '<section class="settings-card" id="schedule"><div class="settings-card-head"><div><h2>예약 알림</h2>'
        '<p>정한 요일·시각마다 새 기사를 골라 예약 소식함에 넣어 드립니다.</p></div>'
        '<span class="status-tag ready" id="schedule-state">사용</span></div>'
        '<div class="form-grid"><label class="form-field"><span class="field-label">예약 시각</span>'
        f'<input class="field-control" type="time" name="collection_time" id="collection-time" value="{escape(schedule.time, quote=True)}" required></label>'
        '<label class="form-field"><span class="field-label">시간대</span><select class="field-control" name="timezone" id="schedule-timezone">'
        '<option value="Asia/Seoul">Asia/Seoul (KST)</option></select><span class="field-help">한국 표준시를 기준으로 실행합니다.</span></label></div>'
        '<div class="toggle-row"><div class="toggle-copy"><strong>예약 알림 사용</strong><span>끄면 예약 시각이 되어도 소식을 만들지 않습니다.</span></div>'
        f'<label class="switch-control"><input class="sr-only" id="schedule-enabled" name="schedule_enabled" type="checkbox" {checked(schedule.enabled)} aria-label="예약 알림 사용"><span class="switch" aria-hidden="true"></span></label></div>'
        f'<div class="choice-row"><span class="field-label" id="days-label">요일</span><div class="chips" role="group" aria-labelledby="days-label" id="schedule-days">{days}</div></div>'
        f'<div class="choice-row"><span class="field-label" id="sources-label">받을 기사</span><div class="chips" role="group" aria-labelledby="sources-label" id="schedule-sources">{sources}</div></div>'
        f'<div class="form-grid"><label class="form-field"><span class="field-label">한 번에 최대</span><select class="field-control" id="schedule-max">{max_options}</select></label>'
        '<div class="form-field"><span class="field-label">다음 예약</span><span class="field-help" id="schedule-preview" role="status"></span></div></div>'
        '<div class="settings-actions inline-actions"><button class="secondary-button" type="button" id="run-now">지금 한 번 받아보기</button>'
        '<a class="text-button" href="/inbox">예약 소식함 보기</a></div>'
        '<p class="settings-feedback" id="run-feedback" role="status" aria-live="polite"></p></section>'
        # 검색·관심 설정
        '<section class="settings-card" id="interests"><div class="settings-card-head"><div><h2>검색·관심 설정</h2>'
        f'<p>선호 검색어와 카테고리 표시 순서를 정합니다. 관심 카테고리: {escape(interest_text)}</p></div></div>'
        '<div class="form-grid"><div class="form-field full"><label class="field-label" for="keyword-input">선호 검색어</label>'
        '<div class="tag-input" id="keyword-preview" aria-label="선호 검색어 목록"></div>'
        '<div class="keyword-add"><input class="field-control" id="keyword-input" maxlength="30" placeholder="예: 멀티모달, AI 에이전트, HBM" aria-describedby="keyword-help keyword-error">'
        '<button class="secondary-button" type="button" id="keyword-add">추가</button></div>'
        '<span class="field-help" id="keyword-help">최대 3개까지 저장합니다. 메인 검색창 아래 칩으로 보이고, 예약 알림의 기사 고르기에 쓰입니다.</span>'
        '<span class="field-error" id="keyword-error" role="alert"></span></div>'
        '<label class="form-field"><span class="field-label">수집 출처</span><select class="field-control" name="source_group">'
        '<option value="all">승인 출처 전체</option><option value="official">공식 기업 블로그</option><option value="research">연구·개발 플랫폼</option></select>'
        '<span class="field-help">출처 그룹 선택은 화면 예시입니다.</span></label>'
        '<div class="form-field full"><span class="field-label" id="category-order-label">카테고리 표시·순서</span>'
        '<ol class="category-order" id="category-order" aria-labelledby="category-order-label"></ol>'
        '<span class="field-help">메인 화면의 카테고리 칩이 이 순서로 보이며, 끈 카테고리는 숨겨집니다. '
        '<button type="button" class="auth-link" id="category-reset">기본 순서로</button></span></div></div></section>'
        # 노출·알림
        '<section class="settings-card" id="display"><div class="settings-card-head"><div><h2>노출·알림</h2>'
        '<p>기본 뉴스 개수와 알림을 받을 채널을 선택합니다.</p></div></div><div class="form-grid">'
        f'<label class="form-field"><span class="field-label">기본 노출 수</span><select class="field-control" name="display_count" id="display-count">{count_options}</select>'
        '<span class="field-help">메인 목록에 보이는 기사 수입니다.</span></label>'
        '<div class="form-field"><span class="field-label">알림 채널</span><span class="field-help">인앱 알림은 왼쪽 메뉴의 예약 소식함에 "새" 표시로 알려 드립니다.</span></div></div>'
        '<div class="toggle-row"><div class="toggle-copy"><strong>인앱 알림</strong><span>새 예약 소식을 DAIT 안에서 표시합니다.</span></div>'
        f'<label class="switch-control"><input class="sr-only" id="in-app-notification" name="in_app_notification" type="checkbox" {checked(settings.in_app_notification)} aria-label="인앱 알림"><span class="switch" aria-hidden="true"></span></label></div>'
        '<div class="toggle-row"><div class="toggle-copy"><strong>메일 알림</strong><span>선택은 저장되지만 메일 발송은 이메일 등록·인증과 함께 후속 단계에서 연결합니다.</span></div>'
        f'<label class="switch-control"><input class="sr-only" id="email-notification" name="email_notification" type="checkbox" {checked(settings.email_notification)} aria-label="메일 알림"><span class="switch" aria-hidden="true"></span></label></div></section>'
        # 계정·정책 (변경 없음)
        '<section class="settings-card" id="account"><div class="settings-card-head"><div><h2>계정·정책</h2><p>현재 계정과 개인정보·탈퇴 관련 안내를 확인합니다.</p></div>'
        f'<span class="category-tag ai">{escape(user)}</span></div>'
        '<div class="toggle-row"><div class="toggle-copy"><strong>개인정보 처리 안내</strong><span>현재 테스트 환경에서 사용하는 정보를 확인합니다.</span></div><button class="secondary-button" type="button" data-open-dialog="privacy-dialog">내용 보기</button></div>'
        '<div class="toggle-row danger-zone"><div class="toggle-copy"><strong>회원탈퇴</strong><span>테스트 계정과 운영용 회원탈퇴 기능 안내</span></div><button class="secondary-button" type="button" data-open-dialog="withdrawal-dialog">탈퇴 안내</button></div></section>'
        '<div class="settings-footer"><p id="settings-feedback" class="settings-feedback" role="status" aria-live="polite"></p>'
        '<div class="settings-actions"><button class="secondary-button" type="reset">변경 취소</button><button class="primary-button" type="submit" id="settings-save">설정 저장</button></div></div>'
        '</form></div>'
        f'<script type="application/json" id="settings-data">{data}</script>'
    )
    dialogs = (
        '<dialog class="settings-dialog" id="privacy-dialog" aria-labelledby="privacy-title"><div class="login-card"><div class="login-top"><h2 id="privacy-title">개인정보 처리 안내</h2><button class="card-close" type="button" data-close-dialog aria-label="안내 닫기">×</button></div>'
        '<p class="card-note">현재 회원 계정·로그인 세션과 계정별 관심 카테고리를 사용합니다. 설정 화면에서 저장한 선호 검색어·카테고리 표시 순서·예약 알림·노출 설정과 예약 소식함은 계정별로 보관됩니다.</p>'
        '<p class="card-note">이메일 인증 및 운영용 개인정보 처리방침은 아직 제공되지 않습니다. 보관 기간과 삭제 정책은 운영 기능을 구현할 때 확정합니다.</p><button class="primary-button" type="button" data-close-dialog>확인</button></div></dialog>'
        '<dialog class="settings-dialog" id="withdrawal-dialog" aria-labelledby="withdrawal-title"><div class="login-card"><div class="login-top"><h2 id="withdrawal-title">회원탈퇴 안내</h2><button class="card-close" type="button" data-close-dialog aria-label="안내 닫기">×</button></div>'
        '<p class="card-note">회원탈퇴 기능은 아직 제공되지 않으며, 이 화면에서 계정이나 기사가 삭제되지 않습니다.</p><p class="card-note">실제 회원 관리 도입 후 탈퇴 확인과 데이터 처리 절차를 연결할 예정입니다.</p><button class="primary-button" type="button" data-close-dialog>확인</button></div></dialog>'
    )
    result = shell(content, user, active='settings', dialogs=dialogs, inbox_unseen=inbox_unseen)
    return result.replace('</body>', '<script src="/assets/settings.js" defer></script></body>')


def _digest_time(stamp):
    local = datetime.fromtimestamp(stamp, timezone(timedelta(hours=9)))
    return f"{local.month}월 {local.day}일 ({WEEKDAY_NAMES[local.weekday()]}) {local:%H:%M}"


def _kst_text(raw):
    # 메인 카드와 같은 "2026.11.09 18:30 KST" 형식으로 맞춥니다.
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone(timedelta(hours=9))).strftime("%Y.%m.%d %H:%M KST")


def _digest_card(rank, item):
    link = '/article/' + quote(item.article_id, safe='')
    published = escape(_kst_text(item.published_at))
    return (f'<li class="article news-card digest-card"><div class="rank" aria-label="목록 {rank}번째">{rank}</div>'
            f'<div class="news-main"><p class="category-tag ai">{escape(item.categories)}</p>'
            f'<h3 class="news-title"><a href="{link}">{escape(item.title)}</a></h3>'
            f'<div class="news-meta"><span>{escape(item.source)}</span><span class="meta-dot"></span><time>{published}</time></div>'
            f'<p class="digest-reason">받은 이유: {escape(item.reason)}</p></div>'
            f'<div class="card-actions"><a class="primary-button" href="{link}">상세 보기</a></div></li>')


def render_inbox(user, state):
    """KAN-10 예약 소식함. 열 때 새 소식 표시를 보여주고, 저장 상태는 라우터가 읽음으로 바꿉니다."""
    sections = []
    for digest in state.digests:
        cards = ''.join(_digest_card(rank, item) for rank, item in enumerate(digest.items, 1))
        body = f'<ol class="news-list">{cards}</ol>' if cards else '<p class="card-note digest-empty">이번에는 조건에 맞는 새 기사가 없었습니다.</p>'
        new_tag = '' if digest.seen else '<span class="status-tag ready">새 소식</span>'
        title = f'{_digest_time(digest.created_at)} {"미리 받기" if digest.manual else "예약 소식"} · {len(digest.items)}건'
        sections.append(f'<section class="digest" aria-label="{escape(title, quote=True)}"><div class="result-meta"><strong>{escape(title)}</strong>{new_tag}</div>{body}</section>')
    empty = ('<section class="panel digest-empty-state"><h2 class="panel-title">아직 받은 예약 소식이 없습니다</h2>'
             '<p class="card-note">설정에서 요일과 시각을 정하면 그때마다 새 기사를 골라 드립니다.</p>'
             '<a class="primary-button" href="/settings#schedule">예약 알림 설정</a></section>')
    content = ('<div class="page-head"><div><p class="eyebrow">Scheduled Briefing</p><h1 class="page-title">예약 소식함</h1>'
               '<p class="page-description">예약 알림이 골라 둔 기사입니다. 최근 30개까지 보관합니다.</p></div>'
               '<div class="page-head-actions"><a class="secondary-button" href="/settings#schedule">예약 알림 설정</a></div></div>'
               + (''.join(sections) or empty))
    return shell(content, user, active='inbox')


def render_cards(cards, query, scores):
    items = []
    for rank, card in enumerate(cards, 1):
        summary = card["summary"]
        tone, label = summary_status(summary)
        link = '/article/' + quote(str(card['id']), safe='')
        points = ''.join(f'<li>{escape(line)}</li>' for line in summary['lines'])
        summary_html = f'<ul class="summary-list">{points}</ul>' if points else f'<p class="empty-summary">{escape(summary["message"])}</p>'
        score = (scores or {}).get(card['id'])
        similarity = (f'<span class="similarity">의미 유사도 <strong>{score:.3f}</strong></span>' if score is not None else '<span class="similarity pending">의미 유사도 계산 전</span>') if query else ''
        original = safe_url(card.get('url'))
        original_button = f'<a class="secondary-button" href="{escape(original, quote=True)}" target="_blank" rel="noopener noreferrer">원문 열기 ↗</a>' if original else '<span class="no-source">원문 링크 없음</span>'
        items.append(f'''<li class="article news-card" data-article-id="{escape(str(card['id']), quote=True)}"><div class="rank" aria-label="목록 {rank}번째">{rank}</div><div class="news-main"><p class="category-tag ai">{escape(card['categories'] or '기타')}{' · 해외' if card['foreign'] else ''}</p><h2 class="news-title"><a href="{link}" data-detail>{escape(card['title'])}</a></h2><div class="news-meta"><span>{escape(card['source'])}</span><span class="meta-dot"></span><time>{escape(card['date'])}</time></div>{similarity}</div><div class="summary-box"><p class="summary-title">✦ AI 3줄 요약</p>{summary_html}</div><div class="card-actions"><span class="status-tag {tone}">{label}</span><a class="primary-button" href="{link}" data-detail>상세 보기</a>{original_button}</div></li>''')
    return ''.join(items)


def render_main(cards, user, query, scores, interests, category="", sort="rank", categories=(), prefs=None):
    if not query:
        sort = "latest"
    heading = f"{user}님을 위한 뉴스" if user and interests else "오늘의 AI 뉴스"
    intro = (f"관심사: {' · '.join(interests)} · 나에게 맞는 뉴스를 한눈에 확인하세요." if interests
             else "전체 최신 뉴스를 표시합니다. 관심 카테고리를 설정하면 맞춤 뉴스를 볼 수 있습니다.") if user else "오늘의 주요 뉴스와 AI 3줄 요약을 한눈에 확인하세요."
    params = {'q': query, 'sort': sort}
    chips = []
    for value in ('', *categories):
        href = '/?' + urlencode({**params, 'category': value})
        chips.append(f'<a class="chip {"active" if value == category else ""}" href="{escape(href, quote=True)}" data-category="{escape(value, quote=True)}">{escape(value or "전체")}</a>')
    order = "키워드와 의미 유사도 결합순" if query and scores is not None and sort == 'rank' else "최신순"
    if query and scores is not None and sort == 'latest':
        order = "관련도 상위 결과 · 최신순"
    if query and scores is None:
        order = "키워드 일치 · 최신순"
    empty = ("관심사와 검색어에 모두 일치하는 기사가 없습니다." if user and interests else "검색어에 일치하는 기사가 없습니다.") if query else "표시할 기사가 없습니다. 다른 카테고리를 선택해 주세요."
    empty_title = "검색 결과가 없습니다"
    results = render_cards(cards, query, scores) or f'<li class="empty-result"><strong>{empty_title}</strong><p>{empty}</p><a href="/">기본 목록으로 돌아가기</a></li>'
    customize = ('<a class="secondary-button interest-edit" href="/interests">' + ('관심 카테고리 변경' if interests else '관심 카테고리 설정') + '</a>') if user else ''
    content = f'''<div class="page-head"><div><p class="eyebrow">Daily Intelligence</p><h1 class="page-title">{escape(heading)}</h1><p class="page-description">{escape(intro)}</p></div><div class="page-head-actions"><span class="date-chip">RSS 기반 · 최대 {prefs.display_count if prefs else 10}개</span>{customize}</div></div>
    <section aria-label="뉴스 검색"><form class="search toolbar" method="get" action="/" role="search"><label class="search-box"><span class="sr-only">기사 검색</span><span class="search-symbol" aria-hidden="true">⌕</span><input class="search-input" id="query" name="q" type="search" maxlength="200" value="{escape(query, quote=True)}" placeholder="통합 검색 (키워드, 기업, 기술 등)" aria-controls="search-results"></label><button class="primary-button" type="submit">통합 검색</button><a id="clear-search" class="clear-search" href="/">검색 초기화</a></form>{keyword_chips(prefs)}<div class="filter-row"><div class="chips" aria-label="카테고리">{''.join(chips)}</div><label class="sr-only" for="sort">정렬</label><select id="sort" class="select-like"><option value="rank" {'selected' if sort == 'rank' else ''}>검색 관련도순</option><option value="latest" {'selected' if sort == 'latest' else ''}>최신순</option></select></div><p class="search-note">키워드와 의미를 함께 검색합니다. 의미 유사도는 -1~1이며 정확도나 확률이 아닙니다.</p><p id="search-status" class="search-status" role="status" aria-live="polite"></p></section>
    <div><button id="summary-batch" type="button" hidden>요약 준비 다시 시도</button><p id="summary-batch-status" class="card-note" role="status" aria-live="polite"></p></div>
    <section id="search-results" aria-label="기사 목록"><div class="result-meta"><strong>{'검색 결과' if query else '맞춤 추천' if user and interests else '최신 뉴스'} {len(cards)}건</strong><span>{escape(order)}{(' · ' + escape(category)) if category else ''}</span></div><ol class="news-list">{results}</ol></section>'''
    return shell(content, user, query, dialogs=main_dialogs(query), script=True, category=category,
                 inbox_unseen=prefs.inbox_unseen if prefs else 0)


def keyword_chips(prefs):
    """KAN-10: 설정에 저장한 선호 검색어를 검색창 아래 칩으로 보여줍니다. 누르면 그 단어로 검색합니다."""
    if not prefs or not prefs.keywords:
        return ''
    chips = ''.join(f'<button type="button" class="chip keyword-chip" data-keyword="{escape(word, quote=True)}">{escape(word)}</button>'
                    for word in prefs.keywords)
    return (f'<div class="keyword-row" aria-label="선호 검색어"><span class="keyword-label">선호 검색어</span>{chips}'
            '<a class="keyword-edit" href="/settings#interests">설정에서 변경</a></div>')


def render_interests(user, categories, selected, onboarding=False):
    descriptions = {"인공지능": "AI 모델과 서비스, 새로운 활용 소식", "보안": "개인정보 보호와 사이버 보안", "클라우드": "클라우드 서비스와 인프라", "반도체": "반도체 기술과 산업 소식", "개발": "소프트웨어와 개발 기술", "기타": "다양한 분야의 새로운 소식"}
    selected_set = set(selected)
    choices = []
    for index, category in enumerate(categories):
        choices.append(f'''<label class="interest-option"><input id="interest-{index}" type="checkbox" name="categories" value="{escape(category, quote=True)}" {'checked' if category in selected_set else ''}><span class="interest-option-copy"><strong>{escape(category)}</strong><span>{escape(descriptions.get(category, '이 분야의 소식을 받아보세요.'))}</span></span></label>''')
    cancel = ('<button class="secondary-button" id="interests-skip" type="button">다음에 하기</button>' if onboarding
              else '<a class="secondary-button" id="interests-cancel" href="/">취소</a>')
    message = "저장하려면 카테고리를 한 개 이상 선택해주세요. 선택하지 않고 기본 뉴스를 이용해도 됩니다." if categories else "현재 선택할 수 있는 카테고리가 없습니다. 기본 뉴스로 돌아가 이용할 수 있습니다."
    content = f'''<div class="page-head"><div><p class="eyebrow">Personalize Your News</p><h1 class="page-title">{'관심 카테고리 변경' if selected else '어떤 뉴스에 관심 있으세요?'}</h1><p class="page-description">{escape(user)}님이 선택한 관심사로 뉴스와 검색 결과를 맞춤 제공합니다.</p></div></div><section class="panel interests-panel"><div class="panel-head"><h2 class="panel-title">관심 카테고리</h2><span class="interest-count" id="interest-count" role="status" aria-live="polite">{len(selected)}개 선택</span></div><p class="card-note">{message}</p><form id="interests-form" aria-label="관심 카테고리 선택"><div class="interest-tools"><button type="button" class="auth-link" id="interests-all">전체 선택</button><button type="button" class="auth-link" id="interests-clear">선택 해제</button></div><fieldset class="interest-options"><legend class="sr-only">관심 카테고리 목록 · 한 개 이상 선택</legend>{''.join(choices)}</fieldset><p class="interest-scope-note">선택한 카테고리 중 하나 이상에 해당하는 기사를 보여드립니다. 설정은 계정별로 저장되며 언제든 변경할 수 있습니다.</p><p id="interests-feedback" class="settings-feedback" role="status" aria-live="polite"></p><a id="interests-login" class="auth-link" href="/" hidden>메인에서 다시 로그인하기</a><div class="settings-actions">{cancel}<button class="primary-button" id="interests-save" type="submit" {'disabled' if not categories else ''}>{'변경 저장' if selected else '선택 완료'}</button></div></form></section>'''
    result = shell(content, user, active='interests')
    return result.replace('</body>', '<script src="/assets/interests.js" defer></script></body>')


def main_dialogs(query):
    return f'''<dialog id="login-dialog" aria-labelledby="login-title"><div class="login-card"><div class="login-top"><h2 id="login-title">로그인</h2><button type="button" id="login-close" aria-label="로그인 창 닫기">×</button></div>
      <form class="login-form" method="post" action="/login"><input type="hidden" name="q" value="{escape(query, quote=True)}"><label for="login-user">아이디</label><input id="login-user" name="user" autocomplete="username" required maxlength="30"><label for="login-password">비밀번호</label><input id="login-password" name="password" type="password" autocomplete="current-password" required maxlength="128"><p id="login-error" class="login-error" role="alert"></p><button class="login-submit primary-button" type="submit">확인</button><p class="auth-navigation">계정이 없으신가요? <button class="auth-link" id="show-signup" type="button">회원가입</button></p></form>
      <form class="signup-form" id="signup-form" method="post" action="/signup" hidden><p class="login-help">아이디와 비밀번호를 입력해 회원가입을 진행해주세요.</p><label for="signup-user">아이디</label><input id="signup-user" name="user" autocomplete="username" required maxlength="30" aria-describedby="signup-user-error"><p class="auth-field-error" id="signup-user-error" aria-live="polite" hidden></p><label for="signup-password">비밀번호</label><input id="signup-password" name="password" type="password" autocomplete="new-password" required minlength="5" maxlength="128" aria-describedby="signup-password-error"><p class="auth-field-error" id="signup-password-error" aria-live="polite" hidden>비밀번호는 최소 5자 이상 입력해주세요</p><label for="signup-password-confirm">비밀번호 확인</label><input id="signup-password-confirm" name="password_confirm" type="password" autocomplete="new-password" required minlength="5" maxlength="128" aria-describedby="signup-password-confirm-error"><p class="auth-field-error" id="signup-password-confirm-error" aria-live="polite" hidden></p><p id="signup-feedback" class="signup-feedback" role="status" aria-live="polite"></p><button class="login-submit primary-button" type="submit">가입하기</button><p class="auth-navigation">이미 계정이 있으신가요? <button class="auth-link" id="show-login" type="button">로그인으로 돌아가기</button></p></form>
    </div></dialog>
    <dialog id="detail" aria-labelledby="detail-title"><div class="detail-card"><div class="modal-top"><span>오늘의 AI 뉴스 / 뉴스 상세</span><button class="card-close" type="button" aria-label="기사 상세 닫기">×</button></div><section class="article-hero"><div><span class="category-tag ai" id="detail-category"></span><h2 class="article-title" id="detail-title">기사 불러오는 중</h2><p class="news-meta" id="detail-meta"></p><p id="detail-original-title" class="card-note" hidden></p></div><div class="article-actions"><a id="detail-original" class="primary-button" target="_blank" rel="noopener noreferrer" hidden>원문 새 탭 ↗</a><button id="detail-copy" class="secondary-button" type="button" disabled>링크 복사</button><p id="detail-copy-status" class="card-note" role="status"></p></div></section><div class="detail-grid"><div class="content-stack"><section class="panel ai-summary"><h3 class="panel-title">AI 3줄 요약</h3><ol class="key-points" id="detail-ai-lines"></ol><p class="card-note" id="detail-ai-message" role="status"></p><button id="detail-ai-generate" class="secondary-button" type="button" hidden>이 기사 요약 생성</button></section><section class="panel"><h3 class="panel-title" id="detail-description-heading">기사 설명</h3><p class="translation-copy" id="detail-text"></p><p class="card-note" id="detail-note"></p><p class="card-note" id="detail-foreign"></p></section></div><aside class="side-stack"><section class="panel" id="detail-sources" hidden><h3 class="panel-title">원본 정보</h3><div class="source-card"><p class="source-label">Source</p><p class="source-value" id="detail-source-name"></p><a class="source-url" id="detail-source-url" target="_blank" rel="noopener noreferrer"></a></div></section><section class="panel"><h3 class="panel-title">처리 정보</h3><p class="card-note">RSS 설명 기반 AI 요약입니다. 생성 완료는 사실 검증 완료를 의미하지 않습니다.</p></section></aside></div></div></dialog>'''


def render_detail(article, user, summary, translation, date):
    title, source, published, description, content, original_url, foreign, categories = article
    display_title = translation.get('title_ko') or title if translation else title
    tone, label = summary_status(summary)
    original = safe_url(original_url)
    original_button = f'<a class="primary-button" href="{escape(original, quote=True)}" target="_blank" rel="noopener noreferrer">원문 새 탭 ↗</a>' if original else '<span class="card-note">원문 링크 없음</span>'
    points = ''.join(f'<li>{escape(line)}</li>' for line in summary['lines'])
    body = f'''<nav class="breadcrumb"><a href="/">오늘의 AI 뉴스</a><span>/</span><strong>뉴스 상세</strong></nav><section class="article-hero"><div><div class="news-meta"><span class="category-tag ai">{escape(categories or '기타')}</span><span class="status-tag {tone}">{label}</span></div><h1 class="article-title">{escape(display_title)}</h1><p class="news-meta">{escape(source)} · {escape(date)}</p></div><div class="article-actions">{original_button}<button type="button" class="secondary-button" id="standalone-copy" {'disabled' if not original else ''}>링크 복사</button><p id="copy-status" class="card-note" role="status"></p></div></section><div class="detail-grid"><div class="content-stack"><section class="panel"><h2 class="panel-title">AI 3줄 요약</h2><ol class="key-points">{points}</ol><p class="card-note">{escape(summary['message'])}</p></section><section class="panel"><h2 class="panel-title">{'원문 RSS 설명' if foreign else '기사 설명'}</h2>{f'<p class="card-note">원문 제목: {escape(title)}</p>' if foreign else ''}<p class="translation-copy">{escape(description or content or '제공된 설명이 없습니다.')}</p><p class="card-note">RSS에서 제공한 설명이며 기사 전문이 아닙니다.</p>{'<p class="card-note">해외 기사 전문 번역은 아직 제공되지 않습니다.</p>' if foreign else ''}</section></div><aside class="side-stack"><section class="panel"><h2 class="panel-title">원본 정보</h2><div class="source-card"><p class="source-label">Source</p><p class="source-value">{escape(source)}</p>{f'<a id="original-url" class="source-url" href="{escape(original, quote=True)}" target="_blank" rel="noopener noreferrer">{escape(original)}</a>' if original else ''}</div><div class="source-card"><p class="source-label">Published</p><p class="source-value">{escape(date)}</p></div></section><section class="panel"><h2 class="panel-title">처리 정보</h2><p class="card-note">{escape(summary['message'])}</p></section></aside></div>'''
    result = shell(body, user, active='detail')
    return result.replace('</body>', '<script src="/assets/detail.js" defer></script></body>')
