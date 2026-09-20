"""UT-PAY-001～006、UT-KEY-001 決済判定の単体テスト（テスト仕様書 8章）。

時刻は日本時間の固定値を使う。実際のDB更新は結合テストで確認する。
"""
from datetime import datetime, timedelta, timezone

import pytest

from payment_rules import (
    check_idempotency,
    inquiry_schedule,
    on_inquiry_result,
    on_payment_timeout,
    on_unresolved_inquiry,
)
from rule_errors import BusinessRuleError

JST = timezone(timedelta(hours=9))


def at(hour, minute):
    return datetime(2026, 6, 1, hour, minute, tzinfo=JST)


def test_UT_PAY_001_タイムアウトはUNKNOWN():
    d = on_payment_timeout()
    assert (d.payment_status, d.order_status) == ("UNKNOWN", "PAYMENT_PENDING")
    assert d.request_new_payment is False


def test_UT_PAY_002_照会成功で同じ注文を確定():
    d = on_inquiry_result("SUCCEEDED")
    assert (d.payment_status, d.order_status) == ("SUCCEEDED", "CONFIRMED")
    assert d.confirm_order and d.consume_inventory
    assert d.request_new_payment is False


def test_UT_PAY_003_照会失敗で未確定と確保解放():
    d = on_inquiry_result("FAILED")
    assert d.confirm_order is False
    assert d.record_failure and d.release_reservation
    assert d.order_status == "PAYMENT_FAILED"


def test_UT_PAY_004_10分時点で未解決なら期限を延長():
    f = on_unresolved_inquiry(at(12, 0), at(12, 10), at(12, 15))
    assert f.reservation_deadline == at(12, 25)
    assert f.release_reservation is False
    assert f.notify_operator is True


def test_UT_PAY_005_期限を短縮しない():
    f = on_unresolved_inquiry(at(12, 0), at(12, 10), at(12, 40))
    assert f.reservation_deadline == at(12, 40)
    assert f.release_reservation is False


def test_UT_PAY_006_照会の予定時刻():
    expected = [at(12, 1), at(12, 5), at(12, 10), at(12, 15), at(12, 20)]
    assert inquiry_schedule(at(12, 0), 5) == expected


def test_UT_KEY_001_既存キー同内容は既存処理を参照():
    assert check_idempotency("hash-A", "hash-A") == "USE_EXISTING"


def test_UT_KEY_001_既存キー異なる内容は409():
    with pytest.raises(BusinessRuleError) as error:
        check_idempotency("hash-A", "hash-B")
    assert (error.value.status_code, error.value.error_code) == (409, "IDEMPOTENCY_CONFLICT")
