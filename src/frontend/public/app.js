/* DAIT 공통 프론트엔드 헬퍼: Bearer 토큰 저장·갱신, 인증 영역 렌더링, API 호출. */
(function () {
  "use strict";

  const ACCESS_KEY = "dait_access_token";
  const REFRESH_KEY = "dait_refresh_token";

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
      const name = escapeHtml(user.email);
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

  function openAuthDialog(signup) {
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
      dialog.addEventListener("click", (e) => {
        if (e.target === dialog) dialog.close();
      });
      dialog.querySelector("#auth-form").addEventListener("submit", onAuthSubmit);
    }
    const form = dialog.querySelector("#auth-form");
    form.innerHTML = signup ? signupFieldsHtml() : loginFieldsHtml();
    dialog.querySelector("#auth-title").textContent = signup ? "회원가입" : "로그인";
    dialog.querySelector("#auth-feedback").textContent = "";
    dialog.showModal();
    dialog._signup = signup;
  }

  function loginFieldsHtml() {
    return (
      '<label for="auth-email">이메일</label><input id="auth-email" name="email" type="email" autocomplete="username" required maxlength="254">' +
      '<label for="auth-password">비밀번호</label><input id="auth-password" name="password" type="password" autocomplete="current-password" required maxlength="128">' +
      '<p class="auth-navigation">계정이 없으신가요? <button class="auth-link" type="button" id="auth-switch">회원가입</button></p>' +
      '<button class="login-submit primary-button" type="submit">로그인</button>'
    );
  }

  function signupFieldsHtml() {
    return (
      '<label for="auth-email">이메일</label><input id="auth-email" name="email" type="email" autocomplete="username" required maxlength="254">' +
      '<label for="auth-password">비밀번호 (8자 이상)</label><input id="auth-password" name="password" type="password" autocomplete="new-password" required minlength="8" maxlength="128">' +
      '<label for="auth-password-confirm">비밀번호 확인</label><input id="auth-password-confirm" name="password_confirm" type="password" autocomplete="new-password" required minlength="8" maxlength="128">' +
      '<label class="auth-check"><input id="auth-terms" name="terms_accepted" type="checkbox" required> 이용약관 및 개인정보 처리에 동의합니다</label>' +
      '<p class="auth-navigation">이미 계정이 있으신가요? <button class="auth-link" type="button" id="auth-switch">로그인</button></p>' +
      '<button class="login-submit primary-button" type="submit">가입하기</button>'
    );
  }

  async function onAuthSubmit(event) {
    event.preventDefault();
    const dialog = document.getElementById("auth-dialog");
    const form = dialog.querySelector("#auth-form");
    const feedback = dialog.querySelector("#auth-feedback");
    const signup = !!dialog._signup;
    const data = new FormData(form);
    if (signup && data.get("password") !== data.get("password_confirm")) {
      feedback.textContent = "비밀번호가 일치하지 않습니다.";
      return;
    }
    const payload = {
      email: data.get("email"),
      password: data.get("password"),
    };
    if (signup) {
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
        const msg =
          (typeof body.message === "string" && body.message) ||
          (body.error && (body.error.message || body.error)) ||
          "처리하지 못했습니다.";
        feedback.textContent = typeof msg === "string" ? msg : "처리하지 못했습니다.";
        return;
      }
      setTokens(body.tokens);
      dialog.close();
      location.reload();
    } catch (_e) {
      feedback.textContent = "서버에 연결하지 못했습니다.";
    } finally {
      controls.forEach((c) => (c.disabled = false));
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    renderAuthArea();
    document.addEventListener("click", (e) => {
      if (e.target && e.target.id === "auth-switch") {
        const dialog = document.getElementById("auth-dialog");
        if (dialog) {
          dialog._signup = !dialog._signup;
          const form = dialog.querySelector("#auth-form");
          form.innerHTML = dialog._signup ? signupFieldsHtml() : loginFieldsHtml();
          dialog.querySelector("#auth-title").textContent = dialog._signup ? "회원가입" : "로그인";
          dialog.querySelector("#auth-feedback").textContent = "";
        }
      }
    });
  });

  window.DAIT = { api, currentUser, clearTokens, getToken, renderAuthArea };
})();
