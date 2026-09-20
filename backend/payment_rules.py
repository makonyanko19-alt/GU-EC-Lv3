"""Wallet決済の結果に応じた判定（テスト仕様書 8章、DEC-05／06）。

実際のDB更新は結合テストで確認する。ここでは「次に何をするか」の判定だけを返す。
通信断・タイムアウトを決済失敗と推定しない。UNKNOWNの間は在庫確保を自動で解放しない。
"""
from dataclasses import dataclass
from datetime import datetime, timedelta

from rule_errors import BusinessRuleError

# 最初のUNKNOWNから1・5・10分後に照会し、以後5分間隔（DEC-05）。
FIRST_INQUIRY_MINUTES = (1, 5, 10)
FOLLOW_UP_INTERVAL_MINUTES = 5
# 10分以降の照会でも未解決なら、処理時刻＋15分まで確保期限を延ばす。
DEADLINE_EXTENSION_MINUTES = 15
NOTIFY_AFTER_MINUTES = 10


@dataclass(frozen=True)
class PaymentDecision:
    payment_status: str
    order_status: str
    request_new_payment: bool = False
    confirm_order: bool = False
    consume_inventory: bool = False
    record_failure: bool = False
    release_reservation: bool = False


def on_payment_timeout() -> PaymentDecision:
    """決済要求がタイムアウトしたとき（UT-PAY-001）。失敗と断定せずUNKNOWNにする。"""
    return PaymentDecision(payment_status="UNKNOWN", order_status="PAYMENT_PENDING")


def on_inquiry_result(result: str) -> PaymentDecision:
    """UNKNOWNの決済を照会した結果に応じた判定（UT-PAY-002／003）。"""
    if result == "SUCCEEDED":
        # 同じ注文の確定と在庫消費へ進む。新しい決済は作らない。
        return PaymentDecision(
            payment_status="SUCCEEDED",
            order_status="CONFIRMED",
            confirm_order=True,
            consume_inventory=True,
        )
    if result == "FAILED":
        return PaymentDecision(
            payment_status="FAILED",
            order_status="PAYMENT_FAILED",
            record_failure=True,
            release_reservation=True,
        )
    # 照会でも結果が出なければUNKNOWNのまま。確保は解放しない。
    return PaymentDecision(payment_status="UNKNOWN", order_status="PAYMENT_PENDING")


@dataclass(frozen=True)
class UnknownFollowUp:
    reservation_deadline: datetime
    release_reservation: bool
    notify_operator: bool


def on_unresolved_inquiry(
    first_unknown_at: datetime,
    processed_at: datetime,
    current_deadline: datetime,
) -> UnknownFollowUp:
    """照会しても未解決だったときの確保期限と通知（UT-PAY-004／005）。

    10分以降の照会では、期限を max(現期限, 処理時刻＋15分) にする。期限は短縮しない。
    """
    elapsed = processed_at - first_unknown_at
    deadline = current_deadline
    notify = elapsed >= timedelta(minutes=NOTIFY_AFTER_MINUTES)
    if notify:
        deadline = max(
            current_deadline,
            processed_at + timedelta(minutes=DEADLINE_EXTENSION_MINUTES),
        )
    return UnknownFollowUp(
        reservation_deadline=deadline,
        release_reservation=False,
        notify_operator=notify,
    )


def inquiry_schedule(first_unknown_at: datetime, count: int) -> list[datetime]:
    """照会の予定時刻を先頭から count 件返す（UT-PAY-006）。"""
    times = [
        first_unknown_at + timedelta(minutes=m) for m in FIRST_INQUIRY_MINUTES
    ]
    while len(times) < count:
        times.append(times[-1] + timedelta(minutes=FOLLOW_UP_INTERVAL_MINUTES))
    return times[:count]


def check_idempotency(
    existing_request_hash: str | None,
    request_hash: str,
) -> str:
    """同じ冪等キーでの再送を判定する（UT-KEY-001、DEC-06）。

    既存なし→"NEW"、同じ内容→"USE_EXISTING"（既存処理を参照し新規決済なし）、
    内容が違う→409 IDEMPOTENCY_CONFLICT。
    """
    if existing_request_hash is None:
        return "NEW"
    if existing_request_hash == request_hash:
        return "USE_EXISTING"
    raise BusinessRuleError(
        409,
        "IDEMPOTENCY_CONFLICT",
        "同じ購入キーで異なる内容が送信されました。",
    )
