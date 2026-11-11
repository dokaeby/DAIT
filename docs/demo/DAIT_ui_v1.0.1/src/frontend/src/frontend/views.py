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


def shell(content, user=None, query="", active="home", dialogs="", script=False, category="", nickname=None, inbox_unseen=0):
    if user and nickname is None:
        from dait.repositories.user_repository import display_nickname
        nickname = display_nickname(user)
    status = f"{escape(nickname)}님" if user and nickname else "회원님" if user else "비로그인"
    logout = '<form method="post" action="/logout"><button class="secondary-button" type="submit">로그아웃</button></form>' if user else ""
    user_button = ('<button class="primary-button" type="button" id="login-open">로그인</button>' if script else '<a class="primary-button" href="/">메인화면</a>') if not user else ''
    signup_button = '<button class="secondary-button" type="button" id="signup-open">회원가입</button>' if script and not user else ''
    settings_button = '<a class="text-button settings-link" href="/settings"' + (' aria-current="page"' if active == 'settings' else '') + '>설정</a>' if user else ''
    settings_nav = '<nav class="nav-group"><span class="nav-label">Workspace</span><a class="nav-item ' + ('active' if active == 'settings' else '') + '" href="/settings">⚙ 설정</a></nav>' if user else ''
    settings_tab = '<a class="mobile-tab ' + ('active' if active == 'settings' else '') + '" href="/settings">⚙<span>설정</span></a>' if user else ''
    interests_nav = ('<a class="nav-item ' + ('active' if active == 'interests' else '') + '" href="/settings#interests">☆ 관심 카테고리</a>') if user else '<span class="nav-item muted">☆ 관심 뉴스 <small>로그인 후</small></span>'
    categories = '<a class="nav-item ' + ('active' if category else '') + '" href="/?category=' + quote('인공지능') + '">✦ AI·기술</a>'
    badge = f'<small class="inbox-badge" aria-label="새 소식 {inbox_unseen}개">새 {inbox_unseen}</small>' if inbox_unseen else ''
    inbox_nav = ('<a class="nav-item ' + ('active' if active == 'inbox' else '') + '" href="/inbox" id="inbox-nav">🔔 예약 소식함' + badge + '</a>') if user else ''
    return f'''<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>DAIT · 오늘의 AI 뉴스</title><link rel="stylesheet" href="/assets/design.css"><link rel="stylesheet" href="/assets/app.css"></head><body>
    <div class="app-shell"><header class="app-header"><a class="brand" href="/" aria-label="DAIT 메인"><span class="brand-mark">DAIT</span><span class="brand-divider"></span><span class="brand-copy">AI 뉴스 큐레이션 서비스</span></a><div class="header-actions"><span class="session-status">{status}</span>{user_button}{signup_button}{logout}{settings_button}</div></header>
    <div class="app-body"><aside class="sidebar" aria-label="주요 탐색"><nav class="nav-group"><span class="nav-label">Discover</span><a class="nav-item {'active' if active == 'home' and not category else ''}" href="/">⌂ 오늘의 AI 뉴스</a>{categories}</nav><nav class="nav-group"><span class="nav-label">Library</span>{interests_nav}{inbox_nav}<span class="nav-item muted">♧ 저장한 뉴스 <small>단계 2</small></span></nav>{settings_nav}<p class="nav-note">RSS 기반 뉴스와 AI 요약을 제공합니다.<br>정확한 내용은 원문을 확인해 주세요.</p></aside><main class="main">{content}</main></div></div>
    <nav class="mobile-tabs {'guest-tabs' if not user else ''}" aria-label="모바일 탐색"><a class="mobile-tab {'active' if not category and active == 'home' else ''}" href="/">⌂<span>오늘의 뉴스</span></a><a class="mobile-tab {'active' if category else ''}" href="/?category={quote('인공지능')}">✦<span>AI·기술</span></a>{settings_tab}</nav>{dialogs}{'<script src="/assets/app.js" defer></script>' if script else ''}</body></html>'''


def _json_for_script(data):
    # <script> 안에 넣는 JSON은 </script> 조기 종료를 막기 위해 < 를 이스케이프합니다.
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")


WEEKDAY_NAMES = ('월', '화', '수', '목', '금', '토', '일')


def render_settings_entry(user, interests, categories=(), state=None, inbox_unseen=0):
    from dait.repositories.user_repository import display_nickname
    current_nickname = display_nickname(user) or ""
    choices = interest_choices(interests)
    data = _json_for_script({"settings": state.settings.model_dump(mode="json"), "saved": state.saved,
                             "available_categories": state.available_categories, "next_run": state.next_run}) if state else "null"
    days = ''.join(f'<button type="button" class="chip day-chip" data-day="{index}" aria-pressed="false">{name}</button>'
                   for index, name in enumerate(WEEKDAY_NAMES))
    sources = ''.join(f'<button type="button" class="chip source-chip" data-source="{value}" aria-pressed="false">{label}</button>'
                      for value, label in (('interests', '관심 카테고리'), ('keywords', '선호 검색어')))
    content = f'''<div class="page-head"><div><p class="eyebrow">Personal Workspace</p><h1 class="page-title">설정</h1><p class="page-description">뉴스 수집 조건, 표시 방식과 알림 채널을 관리합니다.</p></div><span class="phase-tag">단계 3 · 설정</span></div>
    <div class="mockup-note"><strong>안내</strong><span>관심 카테고리는 [설정 완료], 예약 수집·선호 검색어·카테고리 순서·노출 설정은 아래 [설정 저장]으로 계정에 저장됩니다. 메일 발송은 후속 단계입니다.</span></div>
    <div class="settings-layout"><nav class="settings-menu" aria-label="설정 구역"><a class="active" aria-current="location" href="#schedule">예약 수집</a><a href="#interests">관심 설정</a><a href="#display">노출·알림</a><a href="#account">계정·정책</a></nav>
    <div class="settings-sections">
      <section class="settings-card" id="schedule" data-schedule-owner="{escape(user, quote=True)}"><div class="settings-card-head"><div><h2>예약 수집</h2><p>정한 요일·시각마다 새 기사를 골라 예약 소식함에 넣어 드립니다.</p></div><span class="status-tag ready" id="schedule-state">사용</span></div>
        <div class="form-grid"><label class="form-field"><span class="field-label">예약 시간 · 시</span><input class="field-control" id="schedule-hour" type="number" min="0" max="23" step="1" inputmode="numeric" pattern="[0-9]*" value="8" aria-describedby="schedule-hour-help"><span class="field-help" id="schedule-hour-help">0~23시를 직접 입력하거나 화살표로 조절하세요.</span></label><label class="form-field"><span class="field-label">예약 시간 · 분</span><select class="field-control" id="schedule-minute"><option value="00">00분</option><option value="30" selected>30분</option></select></label></div>
        <p class="field-help">시간대: Asia/Seoul (KST) · 30분 단위</p><button class="secondary-button" type="button" id="schedule-add">시간 추가</button>
        <div class="toggle-row"><div class="toggle-copy"><strong>예약 수집 사용</strong><span>끄면 예약 시각이 되어도 소식을 만들지 않습니다.</span></div><label class="switch-control"><input class="sr-only" id="schedule-enabled" type="checkbox" checked aria-label="예약 수집 사용"><span class="switch" aria-hidden="true"></span></label></div>
        <div class="schedule-selection"><strong>선택한 예약 시간 <span id="schedule-count">0 / 5</span></strong><div class="schedule-chips" id="schedule-chips"></div><p class="field-help" id="schedule-feedback" role="status" aria-live="polite"></p><p class="field-help">최대 5개까지 선택할 수 있습니다.</p></div>
        <div class="choice-row"><span class="field-label" id="days-label">요일</span><div class="chips" role="group" aria-labelledby="days-label" id="schedule-days">{days}</div></div>
        <div class="choice-row"><span class="field-label" id="sources-label">받을 기사</span><div class="chips" role="group" aria-labelledby="sources-label" id="schedule-sources">{sources}</div></div>
        <div class="form-grid"><label class="form-field"><span class="field-label">한 번에 최대</span><select class="field-control" id="schedule-max"><option value="5">5건</option><option value="10">10건</option><option value="20">20건</option></select></label><div class="form-field"><span class="field-label">다음 예약</span><span class="field-help" id="schedule-preview" role="status"></span></div></div>
        <div class="settings-actions inline-actions"><button class="secondary-button" type="button" id="run-now">지금 한 번 받아보기</button><a class="text-button" href="/inbox">예약 소식함 보기</a></div>
        <p class="settings-feedback" id="run-feedback" role="status" aria-live="polite"></p>
      </section>
      <section class="settings-card interests-panel" id="interests"><form id="nickname-form" class="form-field"><label class="field-label" for="nickname-input">닉네임 변경</label><input class="field-control" id="nickname-input" maxlength="30" value="{escape(current_nickname, quote=True)}" placeholder="입력하지 않으면 회원님으로 표시됩니다"><span class="field-help">비워두면 회원님으로 표시됩니다.</span><button class="secondary-button" type="submit">닉네임 저장</button><p id="nickname-feedback" class="settings-feedback" role="status" aria-live="polite"></p></form><div class="panel-head"><h2 class="panel-title">관심 카테고리</h2><span class="interest-count" id="interest-count" role="status" aria-live="polite">{len(interests)}개 선택</span></div><p class="card-note">저장하려면 카테고리를 한 개 이상 선택해주세요.</p><form id="interests-form" aria-label="관심 카테고리 선택"><div class="interest-tools"><button type="button" class="auth-link" id="interests-all">전체 선택</button><button type="button" class="auth-link" id="interests-clear">선택 해제</button></div><fieldset class="interest-options interest-groups"><legend class="sr-only">관심 카테고리 목록 중 한 개 이상 선택</legend>{''.join(choices)}</fieldset><p class="interest-scope-note">관심사는 계정별로 저장되며 언제든 변경할 수 있습니다. 선택한 관심사와 일치하는 기사를 메인에서 확인할 수 있습니다.</p><p id="interests-feedback" class="settings-feedback" role="status" aria-live="polite"></p><a id="interests-login" class="auth-link" href="/" hidden>메인에서 다시 로그인하기</a><div class="settings-actions"><button class="primary-button" id="interests-save" type="submit">설정 완료</button></div></form>
        <div class="form-field full kan10-block"><label class="field-label" for="keyword-input">선호 검색어</label><div class="tag-input" id="keyword-preview" aria-label="선호 검색어 목록"></div><div class="keyword-add"><input class="field-control" id="keyword-input" maxlength="30" autocomplete="off" enterkeyhint="done" placeholder="예: 멀티모달, AI 에이전트, HBM" aria-describedby="keyword-help keyword-error"><button class="secondary-button" type="button" id="keyword-add">추가</button></div><span class="field-help" id="keyword-help">최대 3개. 메인 검색창 아래 칩으로 보이고, 예약 수집의 기사 고르기에 쓰입니다.</span><span class="field-error" id="keyword-error" role="alert"></span></div>
        <div class="form-field full kan10-block"><span class="field-label" id="category-order-label">메인 카테고리 칩 표시·순서</span><ol class="category-order" id="category-order" aria-labelledby="category-order-label"></ol><span class="field-help">선택한 관심 카테고리가 메인에 이 순서로 보이며, 끈 항목은 숨겨집니다. 관심 카테고리를 바꿨다면 [설정 완료] 후 새로고침하면 목록이 갱신됩니다. <button type="button" class="auth-link" id="category-reset">기본 순서로</button></span></div>
      </section>
      <section class="settings-card" id="display"><div class="settings-card-head"><div><h2>노출·알림</h2><p>기본 뉴스 개수와 알림을 받을 채널을 선택합니다.</p></div></div><div class="form-grid"><label class="form-field"><span class="field-label">기본 노출 수</span><select class="field-control" name="display_count" id="display-count"><option value="10">10개</option><option value="5">5개</option></select><span class="field-help">메인 목록에 보이는 기사 수입니다.</span></label><div class="form-field"><span class="field-label">알림 채널</span><span class="field-help">인앱 알림은 왼쪽 메뉴의 예약 소식함에 "새" 표시로 알려 드립니다.</span></div></div>
        <div class="toggle-row"><div class="toggle-copy"><strong>인앱 알림</strong><span>새 예약 소식을 DAIT 안에서 표시합니다.</span></div><label class="switch-control"><input class="sr-only" id="in-app-notification" name="in_app_notification" type="checkbox" checked aria-label="인앱 알림"><span class="switch" aria-hidden="true"></span></label></div>
        <div class="toggle-row"><div class="toggle-copy"><strong>메일 알림</strong><span>선택은 저장되지만 메일 발송은 이메일 등록·인증과 함께 후속 단계에서 연결합니다.</span></div><label class="switch-control"><input class="sr-only" id="email-notification" name="email_notification" type="checkbox" aria-label="메일 알림"><span class="switch" aria-hidden="true"></span></label></div>
      </section>
      <section class="settings-card" id="account"><div class="settings-card-head"><div><h2>계정·정책</h2><p>현재 계정과 개인정보·탈퇴 관련 안내를 확인합니다.</p></div><span class="category-tag ai">{escape(user)}</span></div>
        <div class="toggle-row"><div class="toggle-copy"><strong>개인정보 처리 안내</strong><span>현재 테스트 환경에서 사용하는 정보를 확인합니다.</span></div><button class="secondary-button" type="button" data-open-dialog="privacy-dialog">내용 보기</button></div>
        <div class="toggle-row danger-zone"><div class="toggle-copy"><strong>회원탈퇴</strong><span>테스트 계정과 운영용 회원탈퇴 기능 안내</span></div><button class="secondary-button" type="button" data-open-dialog="withdrawal-dialog">탈퇴 안내</button></div>
      </section>
      <div class="settings-footer"><p id="settings-feedback" class="settings-feedback" role="status" aria-live="polite"></p><div class="settings-actions"><button class="secondary-button" type="button" id="settings-reset">변경 취소</button><button class="primary-button" type="button" id="settings-save">설정 저장</button></div></div>
    </div></div>
    <script type="application/json" id="settings-data">{data}</script>'''
    dialogs = '''<dialog class="settings-dialog" id="privacy-dialog" aria-labelledby="privacy-title"><div class="login-card"><div class="login-top"><h2 id="privacy-title">개인정보 처리 안내</h2><button class="card-close" type="button" data-close-dialog aria-label="안내 닫기">×</button></div><p class="card-note">현재 회원 계정·로그인 세션과 계정별 관심 카테고리를 사용합니다. 설정 화면에서 저장한 예약 수집·선호 검색어·카테고리 순서·노출 설정과 예약 소식함은 계정별로 보관됩니다.</p><p class="card-note">이메일 인증 및 운영용 개인정보 처리방침은 아직 제공되지 않습니다. 보관 기간과 삭제 정책은 운영 기능을 구현할 때 확정합니다.</p><button class="primary-button" type="button" data-close-dialog>확인</button></div></dialog>
    <dialog class="settings-dialog" id="withdrawal-dialog" aria-labelledby="withdrawal-title"><div class="login-card"><div class="login-top"><h2 id="withdrawal-title">회원탈퇴 안내</h2><button class="card-close" type="button" data-close-dialog aria-label="안내 닫기">×</button></div><p class="card-note">회원탈퇴 기능은 아직 제공되지 않으며, 이 화면에서 계정이나 기사가 삭제되지 않습니다.</p><p class="card-note">실제 회원 관리 도입 후 탈퇴 확인과 데이터 처리 절차를 연결할 예정입니다.</p><button class="primary-button" type="button" data-close-dialog>확인</button></div></dialog>'''
    result = shell(content, user, active='settings', dialogs=dialogs, inbox_unseen=inbox_unseen)
    return result.replace('</body>', '<script src="/assets/settings.js" defer></script><script src="/assets/interests.js" defer></script></body>')


def keyword_chips(prefs):
    """KAN-10: 설정에 저장한 선호 검색어를 검색창 아래 칩으로 보여줍니다. 누르면 그 단어로 검색합니다."""
    if not prefs or not prefs.keywords:
        return ''
    chips = ''.join(f'<button type="button" class="chip keyword-chip" data-keyword="{escape(word, quote=True)}">{escape(word)}</button>'
                    for word in prefs.keywords)
    return (f'<div class="keyword-row" aria-label="선호 검색어"><span class="keyword-label">선호 검색어</span>{chips}'
            '<a class="keyword-edit" href="/settings#interests">설정에서 변경</a></div>')


def _kst_text(raw):
    # 메인 카드와 같은 "2026.11.09 18:30 KST" 형식으로 맞춥니다.
    try:
        moment = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone(timedelta(hours=9))).strftime("%Y.%m.%d %H:%M KST")


def _digest_time(stamp):
    local = datetime.fromtimestamp(stamp, timezone(timedelta(hours=9)))
    return f"{local.month}월 {local.day}일 ({WEEKDAY_NAMES[local.weekday()]}) {local:%H:%M}"


def _digest_card(rank, item):
    link = '/article/' + quote(item.article_id, safe='')
    return (f'<li class="article news-card digest-card"><div class="rank" aria-label="목록 {rank}번째">{rank}</div>'
            f'<div class="news-main"><p class="category-tag ai">{escape(item.categories)}</p>'
            f'<h3 class="news-title"><a href="{link}">{escape(item.title)}</a></h3>'
            f'<div class="news-meta"><span>{escape(item.source)}</span><span class="meta-dot"></span><time>{escape(_kst_text(item.published_at))}</time></div>'
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
             '<a class="primary-button" href="/settings#schedule">예약 수집 설정</a></section>')
    content = ('<div class="page-head"><div><p class="eyebrow">Scheduled Briefing</p><h1 class="page-title">예약 소식함</h1>'
               '<p class="page-description">예약 수집이 골라 둔 기사입니다. 최근 30개까지 보관합니다.</p></div>'
               '<div class="page-head-actions"><a class="secondary-button" href="/settings#schedule">예약 수집 설정</a></div></div>'
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


def render_main(cards, user, query, scores, interests, category="", sort="rank", categories=(), nickname=None, fallback=False, prefs=None):
    if not query:
        sort = "latest"
    heading = f"{nickname}님을 위한 뉴스" if user and interests and nickname else "회원님을 위한 뉴스" if user and interests else "오늘의 AI 뉴스"
    intro = ("선택한 관심사에 맞는 뉴스를 확인하세요." if interests
             else "전체 최신 뉴스를 표시합니다. 관심 카테고리를 설정하면 맞춤 뉴스를 볼 수 있습니다.") if user else "오늘의 주요 뉴스를 AI 3줄 요약과 함께 확인하세요."
    params = {'q': query, 'sort': sort}
    chips = []
    expandable = bool(user and interests and len(categories) > 5)
    visible = list(categories[:5])
    if expandable and category in categories and category not in visible:
        visible[-1] = category
    for value in ('', *categories):
        href = '/?' + urlencode({**params, 'category': value})
        extra = ' data-extra-interest hidden' if expandable and value and value not in visible else ''
        chips.append(f'<a class="chip {"active" if value == category else ""}" href="{escape(href, quote=True)}" data-category="{escape(value, quote=True)}"{extra}>{escape(value or "전체")}</a>')
    if expandable:
        chips.append(f'<button class="chip interest-expand" type="button" aria-expanded="false" data-interest-expand data-count="{len(categories) - 5}">나머지 {len(categories) - 5}개 펼치기</button>')
    order = "키워드와 의미 유사도 결합순" if query and scores is not None and sort == 'rank' else "최신순"
    if query and scores is not None and sort == 'latest':
        order = "관련도 상위 결과 · 최신순"
    if query and scores is None:
        order = "키워드 일치 · 최신순"
    empty = ("관심사와 검색어에 모두 일치하는 기사가 없습니다." if user and interests else "검색어에 일치하는 기사가 없습니다.") if query else "표시할 기사가 없습니다. 다른 카테고리를 선택해 주세요."
    if not query and user and interests:
        empty = "표시할 최신 기사가 아직 없습니다." if fallback else "선택한 관심사에 해당하는 기사가 아직 없습니다."
    empty_title = "검색 결과가 없습니다"
    results = render_cards(cards, query, scores) or f'<li class="empty-result"><strong>{empty_title}</strong><p>{empty}</p><a href="/">기본 목록으로 돌아가기</a></li>'
    fallback_notice = '<p class="fallback-notice" role="status">선택한 관심사에 맞는 기사가 아직 없어 전체 최신 뉴스를 보여드리고 있어요.</p>' if fallback else ""
    customize = ('<a class="secondary-button interest-edit" href="/settings#interests">' + ('관심 카테고리 변경' if interests else '관심 카테고리 설정') + '</a>') if user else ''
    content = f'''<div class="page-head"><div><p class="eyebrow">Daily Intelligence</p><h1 class="page-title">{escape(heading)}</h1><p class="page-description">{escape(intro)}</p></div></div>
    <section aria-label="뉴스 검색"><form class="search toolbar" method="get" action="/" role="search"><div class="search-box"><label class="sr-only" for="query">관련 검색</label><input class="search-input" id="query" name="q" type="search" maxlength="200" value="{escape(query, quote=True)}" placeholder="통합 검색 (키워드, 기업, 기술 등)" aria-controls="search-results" aria-describedby="search-error"><button class="search-submit" type="submit" aria-label="검색"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"></circle><path d="m16 16 5 5"></path></svg></button><p id="search-error" class="search-error" role="alert" hidden></p></div><a id="clear-search" class="clear-search" href="/">검색 초기화</a></form>{keyword_chips(prefs)}<div class="filter-row"><div class="chips" aria-label="카테고리">{''.join(chips)}</div><label class="sr-only" for="sort" hidden>정렬</label><select id="sort" class="select-like" hidden><option value="rank" {'selected' if sort == 'rank' else ''}>검색 관련도순</option><option value="latest" {'selected' if sort == 'latest' else ''}>최신순</option></select></div><p id="search-status" class="search-status" role="status" aria-live="polite"></p></section>
    <div><button id="summary-batch" type="button" hidden>요약 준비 다시 시도</button><p id="summary-batch-status" class="card-note" role="status" aria-live="polite"></p></div>
    <section id="search-results" aria-label="기사 목록">{fallback_notice}<div class="result-meta"><strong>{'검색 결과' if query else '맞춤 추천' if user and interests and not fallback else '최신 뉴스'} {len(cards)}건</strong></div><ol class="news-list">{results}</ol></section>'''
    return shell(content, user, query, dialogs=main_dialogs(query), script=True, category=category, nickname=nickname,
                 inbox_unseen=prefs.inbox_unseen if prefs else 0)


def interest_choices(selected):
    groups = {
    "AI": [
        "모델·연구",
        "AI 에이전트",
        "개발 도구",
        "오픈소스·로컬 모델",
        "AI 인프라"
    ],
    "경제·비즈니스": [
        "산업 동향",
        "기업·경영",
        "스타트업·투자",
        "금융시장",
        "일자리"
    ],
    "사회·문화": [
        "정책·제도",
        "교육",
        "건강·의료",
        "환경·기후",
        "문화·콘텐츠"
    ]
}
    selected_set = set(selected)
    choices = []
    for group, items in groups.items():
        pills = []
        for category in items:
            checked = 'checked' if category in selected_set else ''
            pills.append(f'<label class="interest-pill"><input type="checkbox" name="categories" value="{escape(category, quote=True)}" {checked}><span class="interest-pill-label"><span class="pill-icon" aria-hidden="true"></span>{escape(category)}</span></label>')
        choices.append(f'<div class="interest-group"><h3>{escape(group)}</h3><div class="interest-pills">{"".join(pills)}</div></div>')
    return choices


def render_interests(user, categories, selected, onboarding=False):
    choices = interest_choices(selected)
    cancel = ('<button class="secondary-button" id="interests-skip" type="button">다음에 하기</button>' if onboarding
              else '<a class="secondary-button" id="interests-cancel" href="/">취소</a>')
    message = "저장하려면 카테고리를 한 개 이상 선택해주세요. 선택하지 않고 기본 뉴스를 이용해도 됩니다." if categories else "현재 선택할 수 있는 카테고리가 없습니다. 기본 뉴스로 돌아가 이용할 수 있습니다."
    content = f'''<div class="page-head"><div><p class="eyebrow">Personalize Your News</p><h1 class="page-title">{'관심 카테고리 변경' if selected else '어떤 뉴스에 관심 있으세요?'}</h1><p class="page-description">관심 있는 주제를 선택해 주세요.</p></div></div><section class="panel interests-panel"><div class="panel-head"><h2 class="panel-title">관심 카테고리</h2><span class="interest-count" id="interest-count" role="status" aria-live="polite">{len(selected)}개 선택</span></div><p class="card-note">{message}</p><form id="interests-form" aria-label="관심 카테고리 선택"><div class="interest-tools"><button type="button" class="auth-link" id="interests-all">전체 선택</button><button type="button" class="auth-link" id="interests-clear">선택 해제</button></div><fieldset class="interest-options interest-groups"><legend class="sr-only">관심 카테고리 목록 · 한 개 이상 선택</legend>{''.join(choices)}</fieldset><p class="interest-scope-note">관심사는 계정별로 저장되며 언제든 변경할 수 있습니다. 선택한 관심사와 일치하는 기사를 메인에서 확인할 수 있습니다.</p><p id="interests-feedback" class="settings-feedback" role="status" aria-live="polite"></p><a id="interests-login" class="auth-link" href="/" hidden>메인에서 다시 로그인하기</a><div class="settings-actions">{cancel}<button class="primary-button" id="interests-save" type="submit" {'disabled' if not categories else ''}>{'변경 저장' if selected else '선택 완료'}</button></div></form></section>'''
    result = shell(content, user, active='interests')
    return result.replace('</body>', '<script src="/assets/interests.js" defer></script></body>')


def main_dialogs(query):
    return f'''<dialog id="login-dialog" aria-labelledby="login-title"><div class="login-card"><div class="login-top"><h2 id="login-title">로그인</h2><button type="button" id="login-close" aria-label="로그인 창 닫기">×</button></div>
      <form class="login-form" method="post" action="/login"><input type="hidden" name="q" value="{escape(query, quote=True)}"><label for="login-user">아이디</label><input id="login-user" name="user" autocomplete="username" required maxlength="30"><label for="login-password">비밀번호</label><input id="login-password" name="password" type="password" autocomplete="current-password" required maxlength="128"><p id="login-error" class="login-error" role="alert"></p><button class="login-submit primary-button" type="submit">확인</button><p class="auth-navigation">계정이 없으신가요? <button class="auth-link" id="show-signup" type="button">회원가입</button></p></form>
      <form class="signup-form" id="signup-form" method="post" action="/signup" hidden><p class="login-help">아이디와 비밀번호를 입력해 회원가입을 진행해주세요.</p><label for="signup-nickname">닉네임</label><input id="signup-nickname" name="nickname" autocomplete="nickname" maxlength="30" aria-describedby="signup-nickname-error"><p class="auth-field-error" id="signup-nickname-error" aria-live="polite" hidden></p><label for="signup-user">아이디</label><input id="signup-user" name="user" autocomplete="username" required maxlength="30" aria-describedby="signup-user-error"><p class="auth-field-error" id="signup-user-error" aria-live="polite" hidden></p><label for="signup-password">비밀번호</label><input id="signup-password" name="password" type="password" autocomplete="new-password" required minlength="5" maxlength="128" aria-describedby="signup-password-error"><p class="auth-field-error" id="signup-password-error" aria-live="polite" hidden>비밀번호는 최소 5자 이상 입력해주세요</p><label for="signup-password-confirm">비밀번호 확인</label><input id="signup-password-confirm" name="password_confirm" type="password" autocomplete="new-password" required minlength="5" maxlength="128" aria-describedby="signup-password-confirm-error"><p class="auth-field-error" id="signup-password-confirm-error" aria-live="polite" hidden></p><p id="signup-feedback" class="signup-feedback" role="status" aria-live="polite"></p><button class="login-submit primary-button" type="submit">가입하기</button><p class="auth-navigation">이미 계정이 있으신가요? <button class="auth-link" id="show-login" type="button">로그인으로 돌아가기</button></p></form>
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
