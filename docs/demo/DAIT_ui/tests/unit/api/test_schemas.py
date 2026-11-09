import pytest
from pydantic import ValidationError

from backend.schemas import InterestSelection, LoginForm, SearchJobRequest, SignupForm


@pytest.mark.ut("UT-AUTH-003")
def test_password_mismatch_rejected():
    with pytest.raises(ValidationError):
        SignupForm(user="usr_test_a", password="abcde", password_confirm="other")


@pytest.mark.extension
@pytest.mark.parametrize("length", [0, 1, 4, 129])
def test_signup_password_boundaries(length):
    with pytest.raises(ValidationError):
        SignupForm(user="usr_test_a", password="a" * length, password_confirm="a" * length)


@pytest.mark.extension
@pytest.mark.parametrize("length", [5, 128])
def test_signup_valid_length(length):
    assert SignupForm(user="usr_test_a", password="a" * length, password_confirm="a" * length)


@pytest.mark.ut("UT-SEARCH-004", "UT-SEARCH-005")
@pytest.mark.parametrize(
    "raw,expected",
    [("  OpenAI  ", "OpenAI"), (" \t\n ", ""), ("AI   cloud", "AI cloud")],
)
def test_login_search_normalization(raw, expected):
    assert LoginForm(user="a", password="abcde", q=raw).q == expected


@pytest.mark.extension
@pytest.mark.parametrize(
    "model,data",
    [
        (SignupForm, dict(user="a", password="abcde", password_confirm="abcde")),
        (LoginForm, dict(user="a", password="abcde")),
        (SearchJobRequest, dict(query="AI")),
        (InterestSelection, dict(categories=["인공지능"])),
    ],
)
def test_extra_fields_forbidden(model, data):
    with pytest.raises(ValidationError):
        model(**data, unexpected="must reject")


@pytest.mark.extension
@pytest.mark.parametrize("score", [-1.01, 1.01, float("nan"), float("inf")])
def test_cosine_threshold_boundary(score):
    with pytest.raises(ValidationError):
        SearchJobRequest(query="AI", min_score=score)


@pytest.mark.extension
def test_secret_not_in_model_repr():
    form = SignupForm(user="a", password="private-password", password_confirm="private-password")
    assert "private-password" not in repr(form)


@pytest.mark.ut("UT-AUTH-002")
@pytest.mark.spec_gap
@pytest.mark.parametrize("email", ["abc", "@example.com", "a" * 256])
def test_document_email_format_policy(email):
    with pytest.raises(ValidationError):
        SignupForm(user=email, password="abcde", password_confirm="abcde")


@pytest.mark.ut("UT-SEARCH-007")
@pytest.mark.spec_gap
def test_document_search_maximum_100():
    with pytest.raises(ValidationError):
        SearchJobRequest(query="a" * 101)
