"""DB 회원 로그인·세션 및 기존 테스트 계정 호환."""
import secrets
from typing import Annotated
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response

from dait import news
from dait.schemas import AuthState, LoginForm, RegisteredUser, SignupForm, SignupResult
from dait.repositories.user_repository import (SESSION_MAX_AGE, DuplicateUsernameError, DuplicateNicknameError, authenticate_member,
                    create_session, create_user, revoke_session, session_identity, username_key)
from dait.preferences import needs_interest_onboarding, user_interests

router = APIRouter(tags=["회원가입·로그인"])
SESSION_COOKIE = "dait_session"


# 기능: 예약 계정·중복 정보를 검사하고 회원가입 정보를 저장한다.
# 입력:
#   form (Annotated[SignupForm, Form()]): 검증된 폼 입력 모델.
# 출력: SignupResult 또는 중복을 알리는 HTTP 409 JSONResponse.
@router.post("/signup", status_code=201, response_model=SignupResult,
             responses={409: {"description": "사용 중이거나 테스트 계정으로 예약된 아이디"}},
             summary="회원가입 정보 저장")
def signup(form: Annotated[SignupForm, Form()]):
    # 기존 테스트 계정과 새 회원이 같은 아이디를 사용하지 않도록 보호합니다.
    if username_key(form.user) in {username_key(name) for name in news.USERS}:
        return JSONResponse({"error": "이미 사용 중인 아이디입니다.", "field_errors": {"user": "이미 사용 중인 아이디입니다."}}, status_code=409)
    try:
        member = create_user(form.user, form.password.get_secret_value(), form.nickname)
    except DuplicateNicknameError as exc:
        return JSONResponse({"error": str(exc), "field_errors": {"nickname": str(exc)}}, status_code=409)
    except DuplicateUsernameError as exc:
        return JSONResponse({"error": str(exc), "field_errors": {"user": str(exc)}}, status_code=409)
    return SignupResult(message="회원가입이 완료되었습니다. 로그인으로 돌아가 가입한 계정으로 로그인해주세요.",
                        user=RegisteredUser(**member))


# 기능: 요청 쿠키의 유효 세션에서 현재 사용자 이름을 구한다.
# 입력:
#   request (Request): 현재 HTTP 요청.
# 출력: 사용자 이름 문자열 또는 None.
def current_user(request: Request) -> str | None:
    identity = session_identity(request.cookies.get(SESSION_COOKIE))
    if identity is None:
        return None
    if identity["kind"] == "test" and identity["username"] not in news.USERS:
        return None
    return identity["username"]


# 기능: 계정을 인증하고 세션 쿠키를 설정해 적절한 화면으로 이동시킨다.
# 입력:
#   request (Request): 현재 HTTP 요청.
#   form (Annotated[LoginForm, Form()]): 검증된 폼 입력 모델.
#   user (Annotated[str | None, Depends(current_user)]): 현재 사용자 이름(비로그인은 None).
# 출력: HTTP 303 RedirectResponse 또는 HTTP 401/409 오류 응답.
@router.post("/login", response_class=RedirectResponse, status_code=303,
             responses={401: {"description": "잘못된 아이디 또는 비밀번호"},
                        409: {"description": "동일 계정 로그인 중"}},
             summary="회원 로그인·계정 전환")
def login(request: Request, form: Annotated[LoginForm, Form()], user: Annotated[str | None, Depends(current_user)]) -> Response:
    password = form.password.get_secret_value()
    test_accounts = {username_key(name): name for name in news.USERS}
    test_name = test_accounts.get(username_key(form.user))
    if test_name:
        identity = ({"id": None, "username": test_name, "kind": "test"}
                    if secrets.compare_digest(password.encode("utf-8"), news.TEST_PASSWORD.encode("utf-8")) else None)
    else:
        identity = authenticate_member(form.user, password)
    if identity is None:
        return JSONResponse({"error": "아이디 또는 비밀번호가 올바르지 않습니다."}, status_code=401)
    if user == identity["username"]:
        return JSONResponse({"error": "이미 로그인되어 있습니다."}, status_code=409)

    show_onboarding = needs_interest_onboarding(identity["username"])
    token = create_session(identity, request.cookies.get(SESSION_COOKIE))
    # 비로그인 → 로그인은 검색 초기화, 로그인 계정 간 전환은 검색어 유지.
    query = form.q if user else ""
    target = "/?" + urlencode({"q": query}) if query else "/"
    if show_onboarding:
        target = "/settings?section=interests#interests"
    response = RedirectResponse(target, status_code=303)
    response.set_cookie(SESSION_COOKIE, token, max_age=SESSION_MAX_AGE, path="/", httponly=True,
                        samesite="lax", secure=request.url.scheme == "https")
    response.delete_cookie("dait_user", path="/", httponly=True, samesite="lax")
    return response


# 기능: 세션과 로그인 쿠키를 폐기하고 메인 화면으로 이동시킨다.
# 입력:
#   request (Request): 현재 HTTP 요청.
# 출력: HTTP 303 RedirectResponse.
@router.post("/logout", response_class=RedirectResponse, status_code=303, summary="로그아웃·세션 폐기")
def logout(request: Request) -> Response:
    revoke_session(request.cookies.get(SESSION_COOKIE))
    response = RedirectResponse("/", status_code=303)
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax", secure=request.url.scheme == "https")
    response.delete_cookie("dait_user", path="/", httponly=True, samesite="lax", secure=False)
    return response


# 기능: 로그인 여부와 계정별 관심사를 응답 모델로 구성한다.
# 입력:
#   user (Annotated[str | None, Depends(current_user)]): 현재 사용자 이름(비로그인은 None).
# 출력: AuthState 객체.
@router.get("/api/auth/me", response_model=AuthState, summary="현재 로그인 상태")
def me(user: Annotated[str | None, Depends(current_user)]) -> AuthState:
    return AuthState(logged_in=user is not None, user=user, interests=list(user_interests(user)))
