"""UT-AUTH-001～004、UT-ACCESS-001、UT-EXP-001 の単体テスト（テスト仕様書 8章）。"""
from datetime import datetime, timedelta, timezone

import pytest

from auth_rules import LoginState, attempt_login, can_access, is_locked, is_within_expiry

JST = timezone(timedelta(hours=9))


def at(hour, minute, second=0):
    return datetime(2026, 6, 1, hour, minute, second, tzinfo=JST)


def test_UT_AUTH_001_失敗9回目はロックしない():
    r = attempt_login(LoginState(failed_count=8), at(12, 0), credentials_ok=False)
    assert r.state.failed_count == 9
    assert r.state.locked_until is None


def test_UT_AUTH_001_失敗10回目で30分ロック():
    r = attempt_login(LoginState(failed_count=9), at(12, 0), credentials_ok=False)
    assert r.state.locked_until == at(12, 30)
    assert r.error_code == "ACCOUNT_LOCKED"


def test_UT_AUTH_002_ロック中は正しい認証情報でも不可で延長しない():
    locked = LoginState(failed_count=10, locked_until=at(12, 30))
    r = attempt_login(locked, at(12, 10), credentials_ok=True)
    assert r.success is False
    assert r.state.locked_until == at(12, 30)


@pytest.mark.parametrize(
    ("now", "locked"),
    [(at(12, 29, 59), True), (at(12, 30, 0), False), (at(12, 30, 1), False)],
    ids=["a_12:29:59", "b_12:30:00", "c_12:30:01"],
)
def test_UT_AUTH_003_解除時刻の境界(now, locked):
    assert is_locked(LoginState(10, at(12, 30)), now) is locked


def test_UT_AUTH_003_解除時に失敗回数0():
    r = attempt_login(LoginState(10, at(12, 30)), at(12, 30, 0), credentials_ok=True)
    assert r.success is True
    assert r.state.failed_count == 0
    # 解除後の失敗は1回目から数え直す。
    r = attempt_login(LoginState(10, at(12, 30)), at(12, 30, 1), credentials_ok=False)
    assert r.state.failed_count == 1


def test_UT_AUTH_004_成功で失敗回数0():
    r = attempt_login(LoginState(failed_count=3), at(12, 0), credentials_ok=True)
    assert r.success is True
    assert r.state.failed_count == 0


@pytest.mark.parametrize(
    ("owner", "allowed"),
    [("user-A", True), ("user-B", False)],
    ids=["a_owner_A", "b_owner_B"],
)
def test_UT_ACCESS_001_所有者本人だけ許可(owner, allowed):
    assert can_access("user-A", owner) is allowed


@pytest.mark.parametrize("target", ["cart", "order"])
@pytest.mark.parametrize(
    ("offset", "valid"),
    [(-1, True), (0, False), (1, False)],
    ids=["a_T-1s", "b_T", "c_T+1s"],
)
def test_UT_EXP_001_有効期限の境界(target, offset, valid):
    # カートと注文照会で別の期限データを使う。
    expires_at = at(12, 0) if target == "cart" else at(18, 30)
    now = expires_at + timedelta(seconds=offset)
    assert is_within_expiry(now, expires_at) is valid
