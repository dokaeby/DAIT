import pytest
from pydantic import ValidationError

from backend.schemas import InterestSelection, LoginForm, SearchJobRequest, SignupForm


# 기능: 확인 비밀번호 불일치 거부 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-003")
def test_password_mismatch_rejected():
    with pytest.raises(ValidationError):
        SignupForm(nickname="Tester", user="usr_test_a", password="abcde", password_confirm="other")


# 기능: 가입 비밀번호 길이 경계 동작을 검증한다.
# 입력:
#   length: 검사할 문자열 길이.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
@pytest.mark.parametrize("length", [0, 1, 4, 129])
def test_signup_password_boundaries(length):
    with pytest.raises(ValidationError):
        SignupForm(nickname="Tester", user="usr_test_a", password="a" * length, password_confirm="a" * length)


# 기능: 허용된 가입 비밀번호 길이 동작을 검증한다.
# 입력:
#   length: 검사할 문자열 길이.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
@pytest.mark.parametrize("length", [5, 128])
def test_signup_valid_length(length):
    assert SignupForm(nickname="Tester", user="usr_test_a", password="a" * length, password_confirm="a" * length)


# 기능: 로그인 폼 검색어 정규화 동작을 검증한다.
# 입력:
#   raw: 변환·검증할 원본 값.
#   expected: 기대하는 검증 결과.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-SEARCH-004", "UT-SEARCH-005")
@pytest.mark.parametrize(
    "raw,expected",
    [("  OpenAI  ", "OpenAI"), (" \t\n ", ""), ("AI   cloud", "AI cloud")],
)
def test_login_search_normalization(raw, expected):
    assert LoginForm(user="a", password="abcde", q=raw).q == expected


# 기능: 요청 모델의 추가 필드 거부 동작을 검증한다.
# 입력:
#   model: 사용할 모델 이름.
#   data: 처리할 요청 또는 결과 데이터.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
@pytest.mark.parametrize(
    "model,data",
    [
        (SignupForm, dict(nickname="Tester", user="a", password="abcde", password_confirm="abcde")),
        (LoginForm, dict(user="a", password="abcde")),
        (SearchJobRequest, dict(query="AI")),
        (InterestSelection, dict(categories=["인공지능"])),
    ],
)
def test_extra_fields_forbidden(model, data):
    with pytest.raises(ValidationError):
        model(**data, unexpected="must reject")


# 기능: 최소 코사인 유사도 경계 동작을 검증한다.
# 입력:
#   score: 검사할 유사도 값.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
@pytest.mark.parametrize("score", [-1.01, 1.01, float("nan"), float("inf")])
def test_cosine_threshold_boundary(score):
    with pytest.raises(ValidationError):
        SearchJobRequest(query="AI", min_score=score)


# 기능: 모델 문자열에서 비밀번호 노출 방지 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.extension
def test_secret_not_in_model_repr():
    form = SignupForm(nickname="Tester", user="a", password="private-password", password_confirm="private-password")
    assert "private-password" not in repr(form)


# 기능: 문서의 이메일 형식 요구사항 동작을 검증한다.
# 입력:
#   email: 검증할 이메일 문자열.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-AUTH-002")
@pytest.mark.spec_gap
@pytest.mark.parametrize("email", ["abc", "@example.com", "a" * 256])
def test_document_email_format_policy(email):
    with pytest.raises(ValidationError):
        SignupForm(nickname="Tester", user=email, password="abcde", password_confirm="abcde")


# 기능: 문서의 검색어 최대 100자 요구사항 동작을 검증한다.
# 입력: 없음.
# 출력: None. 기대와 다르면 assertion 또는 pytest 검증이 실패한다.
@pytest.mark.ut("UT-SEARCH-007")
@pytest.mark.spec_gap
def test_document_search_maximum_100():
    with pytest.raises(ValidationError):
        SearchJobRequest(query="a" * 101)
