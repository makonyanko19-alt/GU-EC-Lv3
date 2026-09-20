import logging
from uuid import UUID, uuid4

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from db import engine

router = APIRouter(prefix="/api/v1/products", tags=["products"])
logger = logging.getLogger(__name__)


def error_response(
    status_code: int,
    error_code: str,
    message: str,
    field: str | None = None,
) -> JSONResponse:
    trace_id = str(uuid4())
    field_errors = []

    if field is not None:
        field_errors.append(
            {
                "field": field,
                "code": error_code,
                "message": message,
            }
        )

    logger.warning("errorCode=%s traceId=%s", error_code, trace_id)

    return JSONResponse(
        status_code=status_code,
        content={
            "errorCode": error_code,
            "message": message,
            "fieldErrors": field_errors,
            "traceId": trace_id,
        },
    )


@router.get("/{productId}")
def get_product(productId: str) -> JSONResponse:
    # UUIDの形式を確認する。
    try:
        product_id = str(UUID(productId))

        if product_id != productId.lower():
            raise ValueError("Invalid UUID format")

    except ValueError:
        return error_response(
            422,
            "INVALID_ID_FORMAT",
            "商品IDはハイフン付きのUUID形式で指定してください。",
            "productId",
        )

    try:
        with engine.connect() as connection:
            # 公開中の商品だけを取得する。
            product = (
                connection.execute(
                    text("""
                    SELECT
                        product_id AS productId,
                        product_code AS productCode,
                        product_name AS productName,
                        description
                    FROM products
                    WHERE product_id = :product_id
                      AND is_published = TRUE
                """),
                    {"product_id": product_id},
                )
                .mappings()
                .first()
            )

            if product is None:
                return error_response(
                    404,
                    "PRODUCT_OR_SKU_NOT_FOUND",
                    "商品が見つかりません。",
                )

            # 有効なSKUに、在庫とサイズ別の裾上げ条件を付ける。
            sku_rows = (
                connection.execute(
                    text("""
                    SELECT
                        s.sku_id AS skuId,
                        s.sku_code AS skuCode,
                        s.color_code AS colorCode,
                        s.color_name AS colorName,
                        s.size_code AS sizeCode,
                        s.selling_price AS sellingPrice,
                        COALESCE(
                            i.on_hand_quantity - i.reserved_quantity,
                            0
                        ) AS availableQuantity,
                        COALESCE(
                            r.is_alteration_available,
                            FALSE
                        ) AS isAlterationAvailable,
                        r.min_inseam_cm AS minInseamCm,
                        r.max_inseam_cm AS maxInseamCm,
                        r.inseam_step_cm AS inseamStepCm
                    FROM skus AS s
                    LEFT JOIN inventories AS i
                        ON i.sku_id = s.sku_id
                    LEFT JOIN product_size_alteration_rules AS r
                        ON r.product_id = s.product_id
                       AND r.size_code = s.size_code
                    WHERE s.product_id = :product_id
                      AND s.is_active = TRUE
                    ORDER BY s.color_code, s.size_code
                """),
                    {"product_id": product_id},
                )
                .mappings()
                .all()
            )

            if not sku_rows:
                return error_response(
                    404,
                    "PRODUCT_OR_SKU_NOT_FOUND",
                    "販売対象のSKUが見つかりません。",
                )

            # 利用可能な仕上げ方法だけを取得する。
            method_rows = connection.execute(text("""
                    SELECT
                        alteration_method_id AS alterationMethodId,
                        method_code AS methodCode,
                        method_name AS methodName,
                        alteration_fee AS alterationFee,
                        additional_business_days AS additionalBusinessDays
                    FROM alteration_methods
                    WHERE is_active = TRUE
                    ORDER BY alteration_fee, method_code
                """)).mappings().all()

    except SQLAlchemyError:
        return error_response(
            503,
            "SERVICE_UNAVAILABLE",
            "商品情報を取得できません。時間をおいて再試行してください。",
        )

    skus = []

    for row in sku_rows:
        sku = dict(row)
        sku["sellingPrice"] = int(sku["sellingPrice"])
        sku["availableQuantity"] = int(sku["availableQuantity"])
        sku["isAvailable"] = sku["availableQuantity"] > 0
        sku["isAlterationAvailable"] = bool(sku["isAlterationAvailable"])
        skus.append(sku)

    methods = []

    for row in method_rows:
        method = dict(row)
        method["alterationFee"] = int(method["alterationFee"])
        methods.append(method)

    result = dict(product)
    result["skus"] = skus
    result["alterationMethods"] = methods

    return JSONResponse(status_code=200, content=result)
