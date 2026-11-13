"""로그인 실패 횟수와 잠금 시각을 Redis에서 원자적으로 기록한다."""

from datetime import datetime

from pydantic import ValidationError

from dait.repositories.redis_repository import RedisLike
from dait.schemas.login_throttle import LoginFailureState

BASE_LOCK_SECONDS = 60
MAX_LOCK_SECONDS = 900
_STATE_TTL_MS = (MAX_LOCK_SECONDS + 60) * 1000
_INVALID_STATE = "로그인 제한 저장소 응답이 올바르지 않습니다."

_REGISTER_FAILURE_LUA = """
local now = tonumber(ARGV[1])
local threshold = tonumber(ARGV[2])
local base = tonumber(ARGV[3])
local maximum = tonumber(ARGV[4])
local count = 0
local last = now
local raw = redis.call('GET', KEYS[1])
if raw then
    local ok, state = pcall(cjson.decode, raw)
    if ok and type(state) == 'table' and type(state.f) == 'number'
       and state.f >= 0 and state.f % 1 == 0 and type(state.lf) == 'number'
       and now - state.lf <= maximum then
        count = state.f
        last = math.max(now, state.lf)
    end
end
count = count + 1
local locked_until = 'null'
if count >= threshold then
    local seconds = base
    local steps = count - threshold
    while steps > 0 and seconds < maximum do
        seconds = math.min(seconds * 2, maximum)
        steps = steps - 1
    end
    locked_until = string.format('%.6f', last + seconds)
end
-- cjson 기본 숫자 정밀도로 기존 Python 타임스탬프가 반올림되지 않게 한다.
local updated = '{"f":' .. string.format('%.0f', count)
    .. ',"lf":' .. string.format('%.6f', last) .. ',"lu":' .. locked_until .. '}'
redis.call('SET', KEYS[1], updated, 'PX', ARGV[5])
return updated
"""


# 입력: Redis 연결과 해시된 로그인 제한 키.
# 출력: 검증된 로그인 실패 상태 또는 None.
# 동작: 기존 Redis JSON을 읽고 타입과 값의 범위를 검증한다.
def read_state(client: RedisLike, key: str) -> LoginFailureState | None:
    """기존 JSON 형식을 유지하면서 저장 상태를 검증한다.

    입력: client는 주입한 Redis 연결이고 key는 해시된 계정 또는 IP 키다.
    출력: 검증한 실패 상태이며 없거나 손상되었으면 None이다.
    기능: 기존 손상 데이터 처리 정책을 유지하며 무타입 dict를 반환하지 않는다.
    """
    raw = client.get(key)
    if not isinstance(raw, (str, bytes)):
        return None
    try:
        return LoginFailureState.model_validate_json(raw)
    except ValidationError:
        return None


# 입력: Redis 연결, 해시 키, 잠금 기준 횟수, 현재 UTC 시각.
# 출력: 원자적으로 저장된 로그인 실패 상태.
# 동작: Lua 한 번으로 실패 횟수 증가와 잠금·TTL 계산을 처리한다.
def register_failure(
    client: RedisLike, key: str, threshold: int, now: datetime
) -> LoginFailureState:
    """조회·증가·잠금 계산·TTL 저장을 Lua 한 번으로 실행한다.

    입력: Redis 연결·해시 키·잠금 기준 횟수·서버 UTC 시각이다.
    출력: 저장 완료한 실패 상태다.
    기능: 서로 다른 프로세스의 동시 실패도 덮어쓰지 않고 기존 JSON·TTL을 유지한다.
    """
    raw = client.eval(
        _REGISTER_FAILURE_LUA,
        1,
        key,
        now.timestamp(),
        threshold,
        BASE_LOCK_SECONDS,
        MAX_LOCK_SECONDS,
        _STATE_TTL_MS,
    )
    if not isinstance(raw, (str, bytes)):
        raise TypeError(_INVALID_STATE)
    return LoginFailureState.model_validate_json(raw)
