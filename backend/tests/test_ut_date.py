"""UT-DATE-001～008 配送予定日の単体テスト（テスト仕様書 7章）。

入力は通常の配送予定日。休日は各ケースで固定した集合を渡す（D-07）。
"""
from datetime import date

from delivery import estimate_delivery_date

NO_HOLIDAYS: set[date] = set()


def test_UT_DATE_001_月曜から3営業日():
    assert estimate_delivery_date(date(2026, 6, 1), [True], NO_HOLIDAYS) == date(2026, 6, 4)


def test_UT_DATE_002_木曜から土日をまたぐ():
    # 金・月・火の3営業日
    assert estimate_delivery_date(date(2026, 6, 4), [True], NO_HOLIDAYS) == date(2026, 6, 9)


def test_UT_DATE_003_土曜が通常予定日():
    assert estimate_delivery_date(date(2026, 6, 6), [True], NO_HOLIDAYS) == date(2026, 6, 10)


def test_UT_DATE_004_登録休日を除外():
    holidays = {date(2026, 6, 2)}
    assert estimate_delivery_date(date(2026, 6, 1), [True], holidays) == date(2026, 6, 5)


def test_UT_DATE_005_月またぎ():
    # 登録休日なし。実際の祝日（5月の連休）は読み込まない。
    assert estimate_delivery_date(date(2026, 4, 30), [True], NO_HOLIDAYS) == date(2026, 5, 5)


def test_UT_DATE_006_補正なしは元の日付():
    assert estimate_delivery_date(date(2026, 5, 7), [False], NO_HOLIDAYS) == date(2026, 5, 7)


def test_UT_DATE_007_補正ありと補正なしの一括配送():
    assert estimate_delivery_date(date(2026, 6, 1), [True, False], NO_HOLIDAYS) == date(2026, 6, 4)


def test_UT_DATE_008_補正2点でも加算は1回():
    assert estimate_delivery_date(date(2026, 6, 1), [True, True], NO_HOLIDAYS) == date(2026, 6, 4)
