"""가입 시 쓸 수 없는 비밀번호(흔한 비밀번호, 이메일 포함)를 판별한다."""

from typing import Literal

# 외부 유출 목록 조회는 네트워크 호출이 필요해 2단계로 미루고, 가장 흔한 값만 로컬에 둔다.
# 길이 8자 미만은 스키마가 먼저 거르므로 8자 이상인 것만 적었다. 모두 소문자로 비교한다.
_COMMON_PASSWORDS = frozenset(
    [
        "password",
        "password1",
        "password12",
        "password123",
        "password1234",
        "passw0rd",
        "p@ssw0rd",
        "p@ssword",
        "12345678",
        "123456789",
        "1234567890",
        "11111111",
        "00000000",
        "12341234",
        "123123123",
        "987654321",
        "111222333",
        "qwertyui",
        "qwerty123",
        "qwerty1234",
        "qwertyuiop",
        "1q2w3e4r",
        "1q2w3e4r5t",
        "1qaz2wsx",
        "zxcvbnm1",
        "asdfghjk",
        "asdf1234",
        "abcd1234",
        "abc12345",
        "abcdefgh",
        "abcd12345",
        "a1b2c3d4",
        "aaaaaaaa",
        "zzzzzzzz",
        "iloveyou",
        "iloveyou1",
        "letmein1",
        "welcome1",
        "welcome123",
        "admin123",
        "administrator",
        "monkey123",
        "dragon123",
        "football",
        "baseball",
        "superman",
        "trustno1",
        "sunshine",
        "princess",
        "master123",
        "shadow123",
        "changeme",
        "change123",
        "default1",
        "test1234",
        "testtest",
        "guest123",
        "login123",
        "secret123",
        "whatever",
        "freedom1",
        "starwars",
        "michael1",
        "jordan23",
        "hello123",
        "hellohello",
        "computer",
        "internet121",
        "korea123",
        "korea1234",
        "seoul1234",
        "dait1234",
        "dait12345",
        "daitdait",
    ]
)
_MIN_LOCAL_PART = 3  # 이 길이보다 짧은 이메일 앞부분은 우연히 겹치기 쉬워 비교하지 않는다.


def weak_password_reason(
    password: str, email: str
) -> Literal["COMMON_PASSWORD", "CONTAINS_EMAIL"] | None:
    """가입에 쓸 수 없는 비밀번호인지, 왜 안 되는지 판단한다.

    입력: password (평문 비밀번호), email (가입 이메일)
    출력: 이유 코드(흔한 비밀번호 / 이메일 앞부분 포함), 쓸 수 있으면 None
    기능: 화면이 이유별 문구를 보여 주려고 이유를 구분한다. 대소문자는 구분하지 않는다.
    """
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return "COMMON_PASSWORD"
    local_part = email.lower().split("@", maxsplit=1)[0]
    if len(local_part) >= _MIN_LOCAL_PART and local_part in lowered:
        return "CONTAINS_EMAIL"
    return None
