"""裾上げ指定を、DBの条件と照らし合わせて検証する。

判定ルール本体は alteration_rules.py にある。このファイルは
SKU・裾上げ条件・仕上げ方法をDBから取得して、ルールへ渡す役割。
カート保存・注文確定からはこの validate_alteration を呼び出す。
"""
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from alteration_rules import (
    ALTERATION_NONE,
    NO_ALTERATION,
    AlterationError,
    AlterationSelection,
    check_alteration_input,
    check_alteration_rule,
    normalize_uuid,
)
from db import engine


def validate_alteration(
    sku_id: str,
    alteration_status: str,
    alteration_method_id: str | None,
    inseam_cm: int | None,
) -> AlterationSelection:
    """裾上げ指定を検証し、問題なければAlterationSelectionを返す。

    問題があればAlterationErrorを発生させる。
    """
    sku_id = normalize_uuid(sku_id, "skuId")
    method_id = check_alteration_input(
        alteration_status, alteration_method_id, inseam_cm
    )
    if alteration_status == ALTERATION_NONE:
        return NO_ALTERATION

    try:
        with engine.connect() as connection:
            # 公開中の商品の、有効なSKUだけを対象にする。
            sku = connection.execute(
                text("""
                    SELECT s.product_id, s.size_code
                    FROM skus AS s
                    JOIN products AS p
                      ON p.product_id = s.product_id
                    WHERE s.sku_id = :sku_id
                      AND s.is_active = TRUE
                      AND p.is_published = TRUE
                """),
                {"sku_id": sku_id},
            ).mappings().first()
            if sku is None:
                raise AlterationError(
                    404,
                    "PRODUCT_OR_SKU_NOT_FOUND",
                    "販売対象のSKUが見つかりません。",
                )

            # 商品とサイズの組み合わせで条件を探す（色には依存しない）。
            rule = connection.execute(
                text("""
                    SELECT
                        is_alteration_available,
                        min_inseam_cm,
                        max_inseam_cm,
                        inseam_step_cm
                    FROM product_size_alteration_rules
                    WHERE product_id = :product_id
                      AND size_code = :size_code
                """),
                {
                    "product_id": sku["product_id"],
                    "size_code": sku["size_code"],
                },
            ).mappings().first()

            method = connection.execute(
                text("""
                    SELECT alteration_fee, additional_business_days
                    FROM alteration_methods
                    WHERE alteration_method_id = :method_id
                      AND is_active = TRUE
                """),
                {"method_id": method_id},
            ).mappings().first()
    except SQLAlchemyError:
        raise AlterationError(
            503,
            "SERVICE_UNAVAILABLE",
            "裾上げ条件を確認できません。時間をおいて再試行してください。",
        )

    return check_alteration_rule(
        method_id,
        inseam_cm,
        dict(rule) if rule is not None else None,
        dict(method) if method is not None else None,
    )
