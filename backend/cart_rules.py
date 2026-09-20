"""カートの数量と明細のまとめ方（テスト仕様書 7章）。

数量は1明細あたり1〜10点。合算後も10点以下でなければならない。
同じSKU・同じ裾上げ指定（有無・仕上げ方法・股下）だけを同じ明細へまとめる。
"""
from dataclasses import dataclass

from rule_errors import BusinessRuleError

MIN_QUANTITY = 1
MAX_QUANTITY = 10


def validate_quantity(quantity: object) -> int:
    """数量の型と範囲を確認する（UT-QTY-001〜003）。"""
    if quantity is None:
        raise BusinessRuleError(
            422, "REQUIRED_FIELD_MISSING", "数量を指定してください。", "quantity"
        )
    if isinstance(quantity, bool) or not isinstance(quantity, int):
        raise BusinessRuleError(
            422, "INVALID_INPUT_TYPE", "数量は整数で指定してください。", "quantity"
        )
    if quantity < MIN_QUANTITY or quantity > MAX_QUANTITY:
        raise BusinessRuleError(
            422,
            "QUANTITY_OUT_OF_RANGE",
            f"数量は{MIN_QUANTITY}～{MAX_QUANTITY}点で指定してください。",
            "quantity",
        )
    return quantity


def validate_added_quantity(current: int, added: object) -> int:
    """既存明細へ加える場合、合算後の数量を確認する（UT-QTY-004）。"""
    added = validate_quantity(added)
    merged = current + added
    if merged > MAX_QUANTITY:
        raise BusinessRuleError(
            422,
            "QUANTITY_OUT_OF_RANGE",
            f"同じ商品・補正内容は合計{MAX_QUANTITY}点までです。",
            "quantity",
        )
    return merged


@dataclass(frozen=True)
class LineKey:
    """同じ明細にまとめてよいかを判定するための組み合わせ。"""

    sku_id: str
    alteration_status: str
    alteration_method_id: str | None
    inseam_cm: int | None


def line_key(
    sku_id: str,
    alteration_status: str,
    alteration_method_id: str | None,
    inseam_cm: int | None,
) -> LineKey:
    """明細キーを作る。キーが等しい追加だけを同じ明細へ合算する（UT-CART-001／002）。"""
    return LineKey(sku_id, alteration_status, alteration_method_id, inseam_cm)
