"""金額計算と税率の確認（テスト仕様書 5章、DEC-01／02／09）。

商品価格・補正料・送料はすべて税込の円（整数）で扱う。
内消費税＝floor(注文の税込合計 × 税率 ÷ (100＋税率))。丸めは注文単位で1回だけ行い、
税を支払額へ足し戻さない。明細が空なら送料も含めてすべて0円にする。
"""
from dataclasses import dataclass

from rule_errors import BusinessRuleError


@dataclass(frozen=True)
class PriceLine:
    """カート・注文の1明細。unit_price と alteration_fee は1点あたりの税込額。"""

    unit_price: int
    quantity: int
    alteration_fee: int = 0


@dataclass(frozen=True)
class OrderTotals:
    subtotal: int             # 商品代金の合計
    alteration_total: int     # 補正料の合計
    shipping_fee: int         # 送料
    total: int                # 税込合計（支払額）
    tax_included: int         # 税込合計に含まれる消費税（内税）
    total_excluding_tax: int  # 税抜相当額


def validate_tax_rate(value: object) -> int:
    """税率の設定値を確認する（UT-TAX-001／002）。

    整数のパーセント値で、0以上100未満だけを受け付ける。
    None・空文字・文字列・小数・True／False は設定値として拒否する。
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise BusinessRuleError(
            422,
            "INVALID_TAX_RATE",
            "税率は0以上100未満の整数で設定してください。",
            "taxRate",
        )
    if value < 0 or value >= 100:
        raise BusinessRuleError(
            422,
            "INVALID_TAX_RATE",
            "税率は0以上100未満の整数で設定してください。",
            "taxRate",
        )
    return value


def calculate_tax_included(total: int, tax_rate: int) -> int:
    """税込合計に含まれる消費税を、注文単位で1回だけ切り捨てて求める。"""
    return total * tax_rate // (100 + tax_rate)


def calculate_totals(
    lines: list[PriceLine],
    shipping_fee: int,
    tax_rate: int,
) -> OrderTotals:
    """明細・送料・税率から注文の金額を計算する（UT-CALC-001〜009）。"""
    tax_rate = validate_tax_rate(tax_rate)

    # 空の明細では送料を加算しない（DEC-09）。
    if not lines:
        return OrderTotals(0, 0, 0, 0, 0, 0)

    subtotal = sum(line.unit_price * line.quantity for line in lines)
    # 補正料は1点あたり。明細補正料＝設定料金×数量（DEC-01）。
    alteration_total = sum(
        line.alteration_fee * line.quantity for line in lines
    )
    total = subtotal + alteration_total + shipping_fee
    tax_included = calculate_tax_included(total, tax_rate)
    return OrderTotals(
        subtotal=subtotal,
        alteration_total=alteration_total,
        shipping_fee=shipping_fee,
        total=total,
        tax_included=tax_included,
        total_excluding_tax=total - tax_included,
    )
