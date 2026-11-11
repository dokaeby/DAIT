/* DAIT 공통 프론트엔드 헬퍼: Bearer 토큰 저장·갱신, 인증 영역 렌더링, API 호출. */
(function () {
  "use strict";

  const ACCESS_KEY = "dait_access_token";
  const REFRESH_KEY = "dait_refresh_token";
  const REMEMBERED_EMAIL_KEY = "dait_remembered_email";
  let checkedNickname = null;
  let nicknameCheck = 0;

  const authStyles = document.createElement("link");
  authStyles.rel = "stylesheet";
  authStyles.href = "/mockup/auth.css";
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
    try {
      if (tokens && tokens.access_token) localStorage.setItem(ACCESS_KEY, tokens.access_token);
      if (tokens && tokens.refresh_token) localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
    } catch (_e) {
      /* 저장소 차단 시에도 화면 동작은 유지한다 */
    }
  }

  function clearTokens() {
    try {
      localStorage.removeItem(ACCESS_KEY);
      localStorage.removeItem(REFRESH_KEY);
    } catch (_e) {
      /* noop */
    }
  }

  async function refreshToken() {
    const refresh = getToken(REFRESH_KEY);
    if (!refresh) return false;
    try {
      const res = await fetch("/v1/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!res.ok) {
        clearTokens();
        return false;
      }
      const data = await res.json();
      setTokens(data);
      return true;
    } catch (_e) {
      return false;
    }
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
    if (res.status === 401 && (await refreshToken())) {
      opts.headers.Authorization = "Bearer " + getToken(ACCESS_KEY);
      res = await fetch(path, opts);
    }
    return res;
  }

  /** 현재 로그인 사용자. 비로그인이면 null. */
  async function currentUser() {
    const access = getToken(ACCESS_KEY);
    if (!access) return null;
    try {
      const res = await api("/v1/me/session");
      if (!res.ok) return null;
      const data = await res.json();
      return data.authenticated && data.user ? data.user : null;
    } catch (_e) {
      return null;
    }
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

  function openAuthDialog(signup, email = "") {
    checkedNickname = null;
    nicknameCheck++;
    let dialog = document.getElementById("auth-dialog");
    if (!dialog) {
      dialog = document.createElement("dialog");
      dialog.id = "auth-dialog";
      dialog.className = "settings-dialog";
      dialog.innerHTML =
        '<div class="login-card"><div class="login-top"><h2 id="auth-title">로그인</h2>' +
        '<button class="card-close" type="button" id="auth-close" aria-label="닫기">×</button></div>' +
        '<form id="auth-form" class="login-form"></form>' +
        '<p id="auth-feedback" class="settings-feedback" role="status" aria-live="polite"></p></div>';
      document.body.appendChild(dialog);
      dialog.querySelector("#auth-close").addEventListener("click", () => dialog.close());
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
    if (!signup && email) {
      form.querySelector("#auth-email").value = email;
      form.querySelector("#auth-remember").checked = getToken(REMEMBERED_EMAIL_KEY) === email;
    }
    dialog.querySelector("#auth-title").textContent = signup ? "회원가입" : "로그인";
    dialog.querySelector("#auth-feedback").textContent = "";
    if (!dialog.open) dialog.showModal();
    dialog._signup = signup;
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

  function loginFieldsHtml() {
    const remembered = getToken(REMEMBERED_EMAIL_KEY) || "";
    return (
      '<label for="auth-email">이메일</label><input id="auth-email" name="email" type="email" autocomplete="username" required maxlength="254" value="' + escapeHtml(remembered) + '">' +
      '<label for="auth-password">비밀번호</label><input id="auth-password" name="password" type="password" autocomplete="current-password" required maxlength="128">' +
      '<label class="auth-check" for="auth-remember"><input id="auth-remember" name="remember_email" type="checkbox"' + (remembered ? ' checked' : '') + '><span>이메일 저장</span></label>' +
      '<button class="login-submit primary-button" type="submit">로그인</button>' +
      '<p class="auth-navigation">계정이 없으신가요? <button class="auth-link" type="button" id="auth-switch">회원가입</button></p>'
    );
  }

  function signupFieldsHtml() {
    return (
      '<label for="auth-email">이메일</label><input id="auth-email" name="email" type="email" autocomplete="username" required maxlength="254">' +
      '<label for="auth-nickname">닉네임 (선택)</label><div class="nickname-row"><input id="auth-nickname" name="nickname" type="text" autocomplete="nickname" maxlength="30" aria-describedby="nickname-feedback nickname-help"><button class="secondary-button" type="button" id="nickname-check">중복 확인</button></div><p id="nickname-help" class="field-help">2~30자 · 비워두면 이메일로 표시됩니다.</p><p id="nickname-feedback" class="settings-feedback" role="status" aria-live="polite"></p>' +
      '<label for="auth-password">비밀번호 (8자 이상)</label><input id="auth-password" name="password" type="password" autocomplete="new-password" required minlength="8" maxlength="128">' +
      '<label for="auth-password-confirm">비밀번호 확인</label><input id="auth-password-confirm" name="password_confirm" type="password" autocomplete="new-password" required minlength="8" maxlength="128">' +
      '<label class="auth-check" for="auth-terms"><input id="auth-terms" name="terms_accepted" type="checkbox" required><span>이용약관 및 개인정보 처리에 동의합니다</span></label>' +
      '<button class="login-submit primary-button" type="submit">가입하기</button>' +
      '<p class="auth-navigation">이미 계정이 있으신가요? <button class="auth-link" type="button" id="auth-switch">로그인</button></p>'
    );
  }

  async function onAuthSubmit(event) {
    event.preventDefault();
    const dialog = document.getElementById("auth-dialog");
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
      payload.terms_accepted = data.get("terms_accepted") === "on";
    }
    const controls = form.querySelectorAll("input, button");
    controls.forEach((c) => (c.disabled = true));
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
      location.reload();
    } catch (_e) {
      feedback.textContent = "서버에 연결하지 못했습니다.";
    } finally {
      controls.forEach((c) => (c.disabled = false));
      if (dialog._signup) updateNicknameSubmit();
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
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

  window.DAIT = { api, currentUser, clearTokens, getToken, renderAuthArea };
})();
