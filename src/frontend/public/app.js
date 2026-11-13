/* DAIT 공통 프론트엔드 헬퍼: Bearer 토큰 저장·갱신, 인증 영역 렌더링, API 호출. */
(function () {
  "use strict";

  const ACCESS_KEY = "dait_access_token";
  const REFRESH_KEY = "dait_refresh_token";
  const REMEMBERED_EMAIL_KEY = "dait_remembered_email";
  let checkedNickname = null;
  let nicknameCheck = 0;
  let sessionPromise = null;
  let sessionSnapshot = null;
  let sessionGeneration = 0;
  let googleReturnPromise = null;
  const SESSION_CACHE_KEY = 'dait_session_ui_v1';
  function invalidateSession() {
    sessionGeneration++;
    sessionPromise = null;
    sessionSnapshot = null;
    try { sessionStorage.removeItem(SESSION_CACHE_KEY); } catch { /* optional UI cache */ }
  }

  const authStyles = document.createElement("link");
  authStyles.rel = "stylesheet";
  authStyles.href = "/mockup/auth.css?v=render-fixes-6";
  document.head.appendChild(authStyles);

  function rememberEmail(email) {
    try {
      if (email) localStorage.setItem(REMEMBERED_EMAIL_KEY, email);
      else localStorage.removeItem(REMEMBERED_EMAIL_KEY);
    } catch (_e) {
      /* Storage may be disabled; login must still work. */
    }
  }

  function getToken(key) {
    try {
      return localStorage.getItem(key);
    } catch (_e) {
      return null;
    }
  }

  function setTokens(tokens) {
    invalidateSession();
    try {
      if (tokens && tokens.access_token) localStorage.setItem(ACCESS_KEY, tokens.access_token);
      if (tokens && tokens.refresh_token) localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    } catch (_e) {
      /* 저장소 차단 시에도 화면 동작은 유지한다 */
    }
  }

  function clearTokens() {
    invalidateSession();
    try { sessionStorage.removeItem('dait_feed_cache_v1'); } catch (_e) { /* noop */ }
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch (_e) {
      /* noop */
    }
  }

  let refreshPromise = null;
  async function refreshToken(expiredAccess) {
    if (refreshPromise) return refreshPromise;
    const perform = async () => {
      const currentAccess = getToken(ACCESS_KEY);
      if (!currentAccess) return false;
      if (currentAccess !== expiredAccess) return true;
      const refresh = getToken(REFRESH_KEY);
      if (!refresh) return false;
      const res = await fetch("/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        if (res.status === 401) {
          if (getToken(REFRESH_KEY) !== refresh) return !!getToken(ACCESS_KEY);
          clearTokens();
          return false;
        }
        throw new TypeError('로그인 상태를 확인하지 못했습니다. 잠시 후 다시 시도해 주세요.');
      }
      const data = await res.json();
      if (getToken(REFRESH_KEY) !== refresh) return !!getToken(ACCESS_KEY);
      setTokens(data);
      return true;
    };
    const pending = navigator.locks?.request
      ? navigator.locks.request('dait-token-refresh', perform)
      : perform();
    refreshPromise = pending;
    try { return await pending; }
    finally { if (refreshPromise === pending) refreshPromise = null; }
  }

  /** 인증이 필요한 API 호출. 401이면 refresh 한 번 재시도한다. */
  async function api(path, options) {
    const opts = Object.assign({ headers: {} }, options || {});
    opts.headers = Object.assign(
      { Accept: "application/json", "Content-Type": "application/json" },
      opts.headers || {}
    );
    const access = getToken(ACCESS_KEY);
    if (access) opts.headers.Authorization = "Bearer " + access;
    let res = await fetch(path, opts);
    if (res.status === 401 && access && (await refreshToken(access))) {
      opts.headers.Authorization = "Bearer " + getToken(ACCESS_KEY);
      res = await fetch(path, opts);
    }
    if (res.status === 401 || (res.ok && (opts.method || 'GET').toUpperCase() !== 'GET' && path.startsWith('/v1/me/'))) invalidateSession();
    return res;
  }

  /** 현재 로그인 사용자. 비로그인이면 null. */
  async function currentUser() {
    if (googleReturnPromise) await googleReturnPromise;
    const access = getToken(ACCESS_KEY);
    if (!access) return null;
    if (!sessionSnapshot) {
      try { sessionSnapshot = JSON.parse(sessionStorage.getItem(SESSION_CACHE_KEY) || 'null'); } catch { /* optional UI cache */ }
    }
    if (sessionSnapshot && sessionSnapshot.access === access && Date.now() - sessionSnapshot.time < 60000) return sessionSnapshot.user;
    if (sessionPromise) return sessionPromise;
    const generation = sessionGeneration;
    const pending = (async () => {
      try {
        const res = await api('/v1/me/session');
        if (!res.ok) return null;
        const data = await res.json();
        const user = data.authenticated && data.user ? { ...data.user, interests: data.interests || [] } : null;
        if (user && generation === sessionGeneration && getToken(ACCESS_KEY) === access) {
          sessionSnapshot = {access: getToken(ACCESS_KEY), user, time: Date.now()};
          try { sessionStorage.setItem(SESSION_CACHE_KEY, JSON.stringify(sessionSnapshot)); } catch { /* optional UI cache */ }
        }
        return getToken(ACCESS_KEY) ? user : null;
      } catch (_e) { return null; }
    })();
    sessionPromise = pending;
    try { return await pending; }
    finally { if (sessionPromise === pending) sessionPromise = null; }
  }

  function escapeHtml(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (ch) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[ch])
    );
  }

  /** 헤더의 인증 영역을 렌더링한다. #auth-area 요소가 있을 때만 동작한다. */
  async function renderAuthArea() {
    document
      .querySelectorAll(".settings-gear")
      .forEach((el) => (el.hidden = true));
    const host = document.getElementById("auth-area");
    if (!host) return;
    const user = await currentUser();
    document
      .querySelectorAll(".settings-gear")
      .forEach((el) => (el.hidden = !user));
    if (user) {
      const name = escapeHtml(user.nickname || user.email);
      host.innerHTML =
        '<span class="session-status">' + name + "님</span>" +
        '<button class="secondary-button" type="button" id="logout-btn">로그아웃</button>';
      host.querySelector("#logout-btn").addEventListener("click", async () => {
        try {
          await api("/v1/auth/logout", { method: "POST", body: "{}" });
        } catch (_e) {
          /* 서버 실패와 무관하게 로컬 세션은 지운다 */
        }
        clearTokens();
        location.reload();
      });
    } else {
      host.innerHTML =
        '<button class="secondary-button" type="button" id="signup-open">회원가입</button>' +
        '<button class="primary-button" type="button" id="login-open">로그인</button>';
      host.querySelector("#login-open").addEventListener("click", () => openAuthDialog(false));
      host.querySelector("#signup-open").addEventListener("click", () => openAuthDialog(true));
    }
  }

  function attachCapsLockHints(form) {
    form.querySelectorAll('input[type="password"]').forEach((input) => {
      if (input.dataset.passwordEnhanced) return;
      input.dataset.passwordEnhanced = 'true';
      const wrapper = document.createElement('div');
      wrapper.className = 'password-hint-wrapper';
      const hint = document.createElement('span');
      hint.id = input.id + '-caps-lock';
      hint.className = 'caps-lock-hint';
      hint.setAttribute('role', 'status');
      hint.setAttribute('aria-live', 'polite');
      hint.hidden = true;
      hint.textContent = 'Caps Lock이 켜져 있습니다.';
      input.setAttribute('aria-describedby', hint.id);
      input.before(wrapper);
      wrapper.append(input, hint);
      const toggle = document.createElement('button');
      toggle.type = 'button';
      toggle.className = 'password-visibility';
      const updateToggle = () => {
        const visible = input.type === 'text';
        toggle.setAttribute('aria-label', visible ? '비밀번호 숨기기' : '비밀번호 표시');
        toggle.setAttribute('aria-pressed', String(visible));
        toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/>' + (visible ? '' : '<path d="m3 3 18 18"/>') + '</svg>';
      };
      toggle.addEventListener('click', () => {
        input.type = input.type === 'password' ? 'text' : 'password';
        updateToggle();
        input.focus({preventScroll: true});
      });
      updateToggle();
      wrapper.append(toggle);
      input.form?.closest('dialog')?.addEventListener('close', () => {
        input.type = 'password'; hint.hidden = true; updateToggle();
      });
      let typed = false;
      const update = (event) => {
        if (event.type === 'keydown' && event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) typed = true;
        if (typeof event.getModifierState === 'function') hint.hidden = !(typed && event.getModifierState('CapsLock'));
      };
      input.addEventListener('keydown', update);
      input.addEventListener('keyup', update);
      input.addEventListener('blur', () => { hint.hidden = true; typed = false; });
    });
  }

  function openAuthDialog(signup, email = "") {
    checkedNickname = null;
    nicknameCheck++;
    let dialog = document.getElementById("auth-dialog");
    if (!dialog) {
      dialog = document.createElement("dialog");
      dialog.id = "auth-dialog";
      dialog.className = "settings-dialog";
      // 모달의 바깥 영역을 누르거나 드래그해도 닫히지 않도록 명시한다.
      dialog.setAttribute("closedby", "closerequest");
      dialog.innerHTML =
        '<div class="login-card"><div class="login-top"><h2 id="auth-title">로그인</h2>' +
        '<button class="card-close" type="button" id="auth-close" aria-label="닫기">×</button></div>' +
        '<form id="auth-form" class="login-form"></form>' +
        '<p id="auth-feedback" class="settings-feedback" role="status" aria-live="polite"></p></div>';
      document.body.appendChild(dialog);
      const closeButton = dialog.querySelector("#auth-close");
      let closePointerStarted = false;
      let escapeRequested = false;
      const trackStart = (event) => {
        closePointerStarted = closeButton.contains(event.target);
        escapeRequested = false;
      };
      dialog.addEventListener(window.PointerEvent ? "pointerdown" : "mousedown", trackStart, true);
      dialog.addEventListener("keydown", (event) => {
        if (event.key === "Escape") escapeRequested = true;
      }, true);
      dialog.addEventListener("cancel", (event) => {
        if (!escapeRequested) event.preventDefault();
        escapeRequested = false;
      });
      closeButton.addEventListener("click", (event) => {
        if (event.detail === 0 || closePointerStarted) dialog.close();
        closePointerStarted = false;
      });
      dialog.addEventListener("change", (e) => {
        if (e.target.id === "auth-remember" && !e.target.checked) rememberEmail("");
      });
      dialog.addEventListener("input", (e) => {
        if (e.target.id === "auth-nickname") {
          checkedNickname = null;
          nicknameCheck++;
          document.getElementById("nickname-feedback").textContent = "";
          updateNicknameSubmit();
        }
      });
      dialog.addEventListener("click", (e) => {
        if (e.target.id === "nickname-check") checkNickname();
      });
      dialog.querySelector("#auth-form").addEventListener("submit", onAuthSubmit);
    }
    const form = dialog.querySelector("#auth-form");
    form.innerHTML = signup ? signupFieldsHtml() : loginFieldsHtml();
    attachCapsLockHints(form);
    configureGoogleLogin(form);
    if (!signup && email) {
      form.querySelector("#auth-email").value = email;
      form.querySelector("#auth-remember").checked = getToken(REMEMBERED_EMAIL_KEY) === email;
    }
    dialog.querySelector("#auth-title").textContent = signup ? "회원가입" : "로그인";
    dialog.querySelector("#auth-feedback").textContent = "";
    if (!dialog.open) dialog.showModal();
    dialog._signup = signup;
    dialog._linkTicket = null;
    form.querySelector("#auth-email").focus({ preventScroll: true });
  }

  function nicknameValue() {
    return (document.getElementById("auth-nickname")?.value || "").normalize("NFKC").trim();
  }

  function updateNicknameSubmit() {
    const value = nicknameValue();
    document.querySelector("#auth-form [type=submit]").disabled = !!value && value !== checkedNickname;
  }

  async function checkNickname() {
    const value = nicknameValue();
    const feedback = document.getElementById("nickname-feedback");
    if (Array.from(value).length < 2 || Array.from(value).length > 30) {
      feedback.textContent = "닉네임은 2~30자로 입력해 주세요.";
      return;
    }
    const sequence = ++nicknameCheck;
    const button = document.getElementById("nickname-check");
    button.disabled = true;
    feedback.textContent = "중복 확인 중…";
    try {
      const res = await fetch("/v1/auth/nickname-availability?" + new URLSearchParams({ nickname: value }));
      const body = await res.json();
      if (sequence !== nicknameCheck || value !== nicknameValue()) return;
      checkedNickname = res.ok && body.available ? value : null;
      feedback.textContent = checkedNickname ? "사용 가능한 닉네임입니다." : res.ok ? "이미 사용 중인 닉네임입니다." : "닉네임을 확인하지 못했습니다. 입력을 확인해 주세요.";
      updateNicknameSubmit();
    } catch (_e) {
      if (sequence === nicknameCheck) feedback.textContent = "중복 확인에 실패했습니다. 다시 시도해 주세요.";
    } finally { button.disabled = false; }
  }

  function googleLoginHtml() {
    return '<div class="google-auth-block"><div class="google-divider"><span>또는</span></div><a class="google-login" href="/v1/auth/google/login" aria-disabled="true" tabindex="-1" aria-describedby="google-notice"><span class="google-symbol" aria-hidden="true">G</span><span>Google로 계속하기</span></a><p class="google-notice" id="google-notice" role="status">Google 로그인 확인 중…</p></div>';
  }
  function configureGoogleLogin(form) {
    const button = form.querySelector('.google-login');
    const notice = form.querySelector('.google-notice');
    button.addEventListener('click', event => {
      if (button.getAttribute('aria-disabled') === 'true') event.preventDefault();
    });
    fetch('/v1/auth/google/status', {headers: {Accept: 'application/json'}})
      .then(response => response.ok ? response.json() : {enabled:false})
      .then(data => {
        button.setAttribute('aria-disabled', String(!data.enabled));
        button.tabIndex = data.enabled ? 0 : -1;
        notice.textContent = data.enabled ? '' : 'Google 로그인 준비 중';
        notice.hidden = !!data.enabled;
      }).catch(() => { notice.textContent = 'Google 로그인 상태를 확인하지 못했습니다.'; });
  }

  function loginFieldsHtml() {
    const remembered = getToken(REMEMBERED_EMAIL_KEY) || "";
    return (
      '<label for="auth-email">이메일</label><input id="auth-email" name="email" type="email" autocomplete="username" required maxlength="254" value="' + escapeHtml(remembered) + '">' +
      '<label for="auth-password">비밀번호</label><input id="auth-password" name="password" type="password" autocomplete="current-password" required maxlength="128">' +
      '<label class="auth-check" for="auth-remember"><input id="auth-remember" name="remember_email" type="checkbox"' + (remembered ? ' checked' : '') + '><span>이메일 저장</span></label>' +
      '<button class="login-submit primary-button" type="submit">로그인</button>' +
      googleLoginHtml() +
      '<p class="auth-navigation">계정이 없으신가요? <button class="auth-link" type="button" id="auth-switch">회원가입</button></p>'
    );
  }

  function signupFieldsHtml() {
    return (
      '<label for="auth-email">이메일</label><input id="auth-email" name="email" type="email" autocomplete="username" required maxlength="254">' +
      '<label for="auth-nickname">닉네임 (선택)</label><div class="nickname-row"><input id="auth-nickname" name="nickname" type="text" autocomplete="nickname" maxlength="30" aria-describedby="nickname-feedback nickname-help"><button class="secondary-button" type="button" id="nickname-check">중복 확인</button></div><p id="nickname-help" class="field-help">2~30자 · 비워두면 이메일로 표시됩니다.</p><p id="nickname-feedback" class="settings-feedback" role="status" aria-live="polite"></p>' +
      '<label for="auth-password">비밀번호 (8자 이상)</label><input id="auth-password" name="password" type="password" autocomplete="new-password" required minlength="8" maxlength="128">' +
      '<label for="auth-password-confirm">비밀번호 확인</label><input id="auth-password-confirm" name="password_confirm" type="password" autocomplete="new-password" required minlength="8" maxlength="128">' +
      '<button class="login-submit primary-button" type="submit">가입하기</button>' +
      googleLoginHtml() +
      '<p class="auth-navigation">이미 계정이 있으신가요? <button class="auth-link" type="button" id="auth-switch">로그인</button></p>'
    );
  }

  async function onAuthSubmit(event) {
    event.preventDefault();
    const dialog = document.getElementById("auth-dialog");
    if (dialog._linkTicket) {
      submitLink(dialog);
      return;
    }
    const form = dialog.querySelector("#auth-form");
    const feedback = dialog.querySelector("#auth-feedback");
    const signup = !!dialog._signup;
    const data = new FormData(form);
    if (signup && nicknameValue() && nicknameValue() !== checkedNickname) {
      feedback.textContent = "닉네임 중복 확인을 완료해 주세요.";
      return;
    }
    if (signup && data.get("password") !== data.get("password_confirm")) {
      feedback.textContent = "비밀번호가 일치하지 않습니다.";
      return;
    }
    const payload = {
      email: data.get("email"),
      password: data.get("password"),
    };
    if (signup) {
      payload.nickname = nicknameValue() || null;
      payload.password_confirm = data.get("password_confirm");
    }
    const controls = form.querySelectorAll("input, button");
    controls.forEach((c) => (c.disabled = true));
    const submitButton = form.querySelector('button[type="submit"]');
    const submitLabel = submitButton ? submitButton.textContent : "";
    if (submitButton) submitButton.textContent = "처리 중…";
    showSlowAuthNotice();
    try {
      const res = await fetch(signup ? "/v1/auth/signup" : "/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(payload),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        if (signup && body.code === "NICKNAME_TAKEN") {
          checkedNickname = null;
          nicknameCheck++;
        }
        const msg =
          (typeof body.message === "string" && body.message) ||
          (body.error && (body.error.message || body.error)) ||
          "처리하지 못했습니다.";
        feedback.textContent = typeof msg === "string" ? msg : "처리하지 못했습니다.";
        return;
      }
      if (signup) {
        openAuthDialog(false, payload.email);
        document.getElementById("auth-feedback").textContent = "가입이 완료되었습니다. 비밀번호를 입력해 로그인해 주세요.";
        document.getElementById("auth-password").focus();
        return;
      }
      setTokens(body.tokens);
      if (!signup) rememberEmail(data.get("remember_email") === "on" ? payload.email : "");
      dialog.close();
      if (body.onboarding_required) {
        location.assign('/settings.html?welcome=1#interests');
        return;
      }
      location.assign('/?language=ko');
    } catch (_e) {
      feedback.textContent = "서버에 연결하지 못했습니다.";
    } finally {
      hideSlowAuthNotice();
      if (submitButton) submitButton.textContent = submitLabel;
      controls.forEach((c) => (c.disabled = false));
      if (dialog._signup) updateNicknameSubmit();
    }
  }

  function showSlowAuthNotice() {
    let notice = document.getElementById("slow-auth-notice");
    if (!notice) {
      notice = document.createElement("dialog");
      notice.id = "slow-auth-notice";
      notice.className = "settings-dialog slow-notice";
      notice.innerHTML =
        '<div class="login-card slow-card">' +
        '<div class="slow-spinner" aria-hidden="true"></div>' +
        '<h2>서버를 깨우는 중입니다</h2>' +
        '<p>무료 서버는 일정 시간 사용하지 않으면 잠시 쉬었다가, 첫 요청에 깨어나는 데 30~60초 정도 걸릴 수 있습니다. 잠시만 기다려 주세요.</p>' +
        '<button class="secondary-button" type="button" id="slow-auth-close">계속 기다리기</button></div>';
      document.body.appendChild(notice);
      notice.querySelector("#slow-auth-close").addEventListener("click", () => notice.close());
    }
    if (!notice.open) notice.showModal();
  }

  function hideSlowAuthNotice() {
    const notice = document.getElementById("slow-auth-notice");
    if (notice && notice.open) notice.close();
  }

  const GOOGLE_ERRORS = {
    email_in_use: "이 이메일은 이미 이메일 로그인으로 가입되어 있습니다. 이메일과 비밀번호로 로그인해 주세요.",
    email_unverified: "구글에서 이메일 인증이 끝나지 않은 계정입니다.",
    google_account_mismatch: "이 이메일에는 다른 구글 계정이 이미 연결되어 있습니다. 기존 방식으로 로그인해 주세요.",
    access_denied: "구글 로그인을 취소했습니다.",
    provider_unavailable: "구글과 연결하지 못했습니다. 잠시 후 다시 시도해 주세요.",
  };

  /** 같은 이메일의 기존 계정이 있을 때, 구글 계정을 연결할지 사용자가 고르는 창. */
  function openLinkDialog(ticket) {
    openAuthDialog(false);
    const dialog = document.getElementById("auth-dialog");
    dialog.querySelector("#auth-title").textContent = "구글 계정 연결";
    dialog.querySelector("#auth-form").innerHTML =
      '<p>이 이메일로 가입된 계정이 이미 있어요. 구글 로그인과 연결할까요?</p>' +
      '<p class="field-help">연결하면 다음부터 구글로 바로 로그인할 수 있어요. 기존 이메일 로그인도 그대로 쓸 수 있고, 원하지 않으면 연결하지 않아도 돼요.</p>' +
      '<label for="link-password">기존 계정 비밀번호</label>' +
      '<input id="link-password" name="password" type="password" autocomplete="current-password" required maxlength="128">' +
      '<button class="login-submit primary-button" type="submit">연결하기</button>' +
      '<button class="secondary-button" type="button" id="link-skip">연결하지 않기</button>';
    dialog._linkTicket = ticket;
    attachCapsLockHints(dialog.querySelector('#auth-form'));
    dialog.querySelector("#link-skip").addEventListener("click", () => {
      openAuthDialog(false);
      document.getElementById("auth-feedback").textContent = "연결하지 않았습니다. 이메일과 비밀번호로 로그인해 주세요.";
    });
    dialog.querySelector("#link-password").focus({ preventScroll: true });
  }

  /** 연결 창의 제출: 연결 표와 기존 비밀번호를 보내 연결하고 로그인한다. */
  async function submitLink(dialog) {
    const feedback = dialog.querySelector("#auth-feedback");
    const password = dialog.querySelector("#link-password").value;
    const controls = dialog.querySelectorAll("#auth-form input, #auth-form button");
    controls.forEach((c) => (c.disabled = true));
    try {
      const res = await fetch("/v1/auth/google/link", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ ticket: dialog._linkTicket, password }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        feedback.textContent =
          res.status === 429
            ? "시도 횟수가 초과됐습니다. 잠시 후 다시 시도해 주세요."
            : res.status === 401 && body.code === "INVALID_CREDENTIALS"
              ? "비밀번호가 맞지 않습니다. 다시 입력해 주세요."
              : "연결 시간이 지났습니다. 구글 로그인을 다시 시도해 주세요.";
        return;
      }
      setTokens(body.tokens);
      dialog.close();
      if (body.onboarding_required) location.assign("/settings.html?welcome=1#interests");
      else location.reload();
    } catch (_e) {
      feedback.textContent = "서버에 연결하지 못했습니다.";
    } finally {
      controls.forEach((c) => (c.disabled = false));
    }
  }

  /** 구글 로그인에서 돌아온 주소의 # 값을 처리한다(교환 코드는 주소창에 남기지 않는다). */
  async function handleGoogleReturn() {
    const hash = new URLSearchParams(location.hash.slice(1));
    const code = hash.get("google");
    const error = hash.get("google_error");
    const linkTicket = hash.get("google_link");
    if (!code && !error && !linkTicket) return false;
    history.replaceState(null, "", location.pathname + location.search);
    if (linkTicket) {
      openLinkDialog(linkTicket);
      return true;
    }
    if (error) {
      openAuthDialog(false);
      document.getElementById("auth-feedback").textContent = GOOGLE_ERRORS[error] || "구글 로그인에 실패했습니다. 다시 시도해 주세요.";
      return true;
    }
    try {
      const res = await fetch("/v1/auth/google/exchange", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ code }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error("exchange failed");
      setTokens(body.tokens);
      if (body.onboarding_required) {
        location.assign("/settings.html?welcome=1#interests");
        return true;
      }
      return false;
    } catch (_e) {
      openAuthDialog(false);
      document.getElementById("auth-feedback").textContent = "구글 로그인을 마치지 못했습니다. 다시 시도해 주세요.";
      return true;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    attachCapsLockHints(document);
    renderAuthArea();
    document.addEventListener("click", (e) => {
      if (e.target && e.target.id === "auth-switch") {
        const dialog = document.getElementById("auth-dialog");
        if (dialog) {
          openAuthDialog(!dialog._signup);
        }
      }
    });
  });

  window.DAIT = { api, currentUser, clearTokens, getToken, renderAuthArea, attachCapsLockHints };
  if (new URLSearchParams(location.hash.slice(1)).has('google') || /google_(error|link)=/.test(location.hash)) {
    googleReturnPromise = handleGoogleReturn();
  }
})();
