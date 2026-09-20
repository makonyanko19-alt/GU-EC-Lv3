"""認証のロック、所有者の確認、有効期限（テスト仕様書 8章、DEC-04）。

連続失敗10回で30分ロックする。ロック解除時刻以上で再試行でき、
成功時・解除時に失敗回数を0に戻す。ロック中の試行でロックを延長しない。
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

LOCK_THRESHOLD = 10
LOCK_MINUTES = 30


@dataclass(frozen=True)
class LoginState:
    failed_count: int = 0
    locked_until: datetime | None = None


@dataclass(frozen=True)
class LoginResult:
    success: bool
    state: LoginState
    error_code: str | None = None


def is_locked(state: LoginState, now: datetime) -> bool:
    """解除時刻より前ならロック中（解除時刻ちょうどは解除済み）。"""
    return state.locked_until is not None and now < state.locked_until


def attempt_login(
    state: LoginState,
    now: datetime,
    credentials_ok: bool,
) -> LoginResult:
    """ログイン試行1回分の結果と、更新後の状態を返す（UT-AUTH-001〜004）。"""
    if is_locked(state, now):
        # ロック中は正しい認証情報でも不可。状態は変えない（延長しない）。
        return LoginResult(False, state, "ACCOUNT_LOCKED")

    if state.locked_until is not None:
        # 解除時刻を過ぎたので、失敗回数を0に戻してから判定する。
        state = LoginState()

    if credentials_ok:
        return LoginResult(True, LoginState())

    failed = state.failed_count + 1
    if failed >= LOCK_THRESHOLD:
        locked = LoginState(failed, now + timedelta(minutes=LOCK_MINUTES))
        return LoginResult(False, locked, "ACCOUNT_LOCKED")
    return LoginResult(False, LoginState(failed), "INVALID_CREDENTIALS")


def can_access(user_id: str, owner_id: str) -> bool:
    """カート・注文の所有者本人だけがアクセスできる（UT-ACCESS-001）。"""
    return user_id == owner_id


def is_within_expiry(now: datetime, expires_at: datetime) -> bool:
    """現在時刻＜有効期限なら有効、期限以上で失効（UT-EXP-001）。"""
    return now < expires_at
