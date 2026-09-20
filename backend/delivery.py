"""配送予定日の計算（テスト仕様書 7章、DEC-03／10）。

入力は注文日ではなく「通常の配送予定日」。裾上げを含む注文は、
その翌日から土日と登録休日を除いて3営業日を加算する。
裾上げ商品が何点あっても、注文全体に1回だけ加算する（一括配送）。
"""
from collections.abc import Iterable
from datetime import date, timedelta

ALTERATION_BUSINESS_DAYS = 3


def is_business_day(day: date, holidays: set[date]) -> bool:
    """土日（weekday 5・6）と登録休日以外を営業日とする。"""
    return day.weekday() < 5 and day not in holidays


def add_business_days(start: date, days: int, holidays: set[date]) -> date:
    """start の翌日から数えて、days 営業日目の日付を返す。"""
    current = start
    counted = 0
    while counted < days:
        current += timedelta(days=1)
        if is_business_day(current, holidays):
            counted += 1
    return current


def estimate_delivery_date(
    normal_delivery_date: date,
    alteration_flags: Iterable[bool],
    holidays: set[date] | None = None,
) -> date:
    """注文の配送予定日を返す（UT-DATE-001〜008）。

    alteration_flags: 注文内の各商品が裾上げありかどうか。
    holidays: 登録休日の集合。実際の祝日を暗黙に読み込まない（D-07）。
    """
    if not any(alteration_flags):
        return normal_delivery_date
    return add_business_days(
        normal_delivery_date, ALTERATION_BUSINESS_DAYS, holidays or set()
    )
