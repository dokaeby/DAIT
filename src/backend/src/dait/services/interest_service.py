"""관심사 카탈로그 구성과 내 관심사 조회·교체 규칙을 처리한다."""

from dait.core.config import Settings
from dait.repositories.db import transaction
from dait.repositories.interest_repository import list_codes, replace_codes
from dait.schemas.interest import (
    GROUP_NAMES,
    INTEREST_NAMES,
    CatalogResponse,
    InterestCode,
    InterestGroup,
    InterestItem,
    MyInterestsResponse,
)
from dait.schemas.user import UserRecord


# 입력: 고정 관심사 코드 하나.
# 출력: 한글 이름과 대주제를 포함한 관심사 항목.
# 동작: 코드 앞부분으로 대주제를 구하고 표시 이름을 결합한다.
def _item(code: InterestCode) -> InterestItem:
    """코드 하나를 화면용 항목으로 바꾼다.

    입력: code (관심사 코드)
    출력: InterestItem (코드, 한글 이름, 대주제)
    기능: 대주제는 코드 앞부분(`ai.models`의 `ai`)에서 얻는다.
    """
    return InterestItem(
        code=code,
        name=INTEREST_NAMES[code],
        group=(
            "_".join(code.value.split(".")[:2])
            if code.value.startswith("en.")
            else code.value.split(".")[0]
        ),
    )


# 입력: 없음.
# 출력: 대주제별로 묶인 전체 관심사 카탈로그.
# 동작: 고정 관심사 코드를 화면 표시용 그룹으로 구성한다.
def get_catalog() -> CatalogResponse:
    """선택 가능한 관심사 전체를 대주제별로 묶어 돌려준다.

    입력: 없음
    출력: CatalogResponse (대주제 3개, 소주제 15개)
    기능: DB를 쓰지 않는 고정 목록이라 로그인 없이 누구나 볼 수 있다.
    """
    items = [_item(code) for code in InterestCode]
    groups = [
        InterestGroup(
            group=group,
            group_name=name,
            interests=[item for item in items if item.group == group],
        )
        for group, name in GROUP_NAMES.items()
    ]
    return CatalogResponse(groups=groups)


# 입력: DB에서 읽은 관심사 코드 문자열 목록.
# 출력: 카탈로그 순서로 정리된 내 관심사 응답.
# 동작: 현재 카탈로그에 존재하는 저장 코드만 화면 항목으로 변환한다.
def _to_response(codes: list[str]) -> MyInterestsResponse:
    """저장된 코드 문자열을 카탈로그 순서의 응답으로 바꾼다.

    입력: codes (DB에서 읽은 코드 문자열)
    출력: MyInterestsResponse (카탈로그 순서)
    기능: 카탈로그에서 빠진 코드는 무시한다(목록이 줄어든 뒤 남은 옛 값 대비).
    """
    saved = set(codes)
    return MyInterestsResponse(interests=[_item(c) for c in InterestCode if c.value in saved])


# 입력: 앱 설정과 인증이 끝난 사용자 ID.
# 출력: 사용자가 저장한 관심사 응답.
# 동작: DB에서 관심사 코드를 조회해 카탈로그 순서로 변환한다.
def list_interests(settings: Settings, user_id: str) -> MyInterestsResponse:
    """사용자 id로 저장된 관심사를 읽는다(로그인 응답에 붙이는 용도).

    입력: settings (앱 설정), user_id (인증이 끝난 사용자의 id)
    출력: MyInterestsResponse (카탈로그 순서, 없으면 빈 목록)
    기능: 호출하는 쪽이 이미 인증한 id만 넘긴다. 요청에서 받은 값을 그대로 넘기지 않는다.
    """
    with transaction(settings.database_url) as conn:
        codes = list_codes(conn, user_id)
    return _to_response(codes)


# 입력: 앱 설정과 인증된 사용자.
# 출력: 본인의 관심사 응답.
# 동작: 요청값이 아닌 인증된 사용자 ID로 관심사를 조회한다.
def get_my_interests(settings: Settings, user: UserRecord) -> MyInterestsResponse:
    """본인의 관심사를 돌려준다.

    입력: settings (앱 설정), user (토큰으로 확인된 본인)
    출력: MyInterestsResponse (선택한 관심사, 없으면 빈 목록)
    기능: 사용자 id는 인증된 user에서만 가져온다(IDOR 방지).
    """
    return list_interests(settings, user.id)


# 입력: 앱 설정, 인증된 사용자, 새 관심사 코드 목록.
# 출력: 저장된 관심사 응답.
# 동작: 본인의 관심사 전체를 한 트랜잭션으로 교체한다.
def replace_my_interests(
    settings: Settings, user: UserRecord, codes: list[InterestCode]
) -> MyInterestsResponse:
    """본인의 관심사를 주어진 목록으로 통째로 바꾼다.

    입력: settings (앱 설정), user (본인), codes (중복 없고 15개 이하인 코드, 빈 목록이면 선택 해제)
    출력: MyInterestsResponse (저장된 결과)
    기능: 한 트랜잭션으로 교체한다. 같은 요청을 반복해도 결과가 같다(멱등).
    """
    with transaction(settings.database_url) as conn:
        replace_codes(conn, user.id, [code.value for code in codes])
    return _to_response([code.value for code in codes])
