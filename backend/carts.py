"""カートAPI（設計 C-01〜C-04）。ゲストは guestCartToken Cookie で識別する。

Cookieにはランダムなトークンを入れ、DBにはそのSHA-256ハッシュだけを保存する。
金額は保存せず、取得のたびに最新の価格・補正料から pricing.py で計算する。
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Request, Response
from sqlalchemy import text
from sqlalchemy.engine import Connection

from alteration import validate_alteration
from alteration_rules import normalize_uuid
from cart_rules import validate_added_quantity, validate_quantity
from db import engine
from pricing import PriceLine, calculate_totals
from rule_errors import BusinessRuleError
from settings import (
    CART_EXPIRY_DAYS,
    GUEST_CART_COOKIE,
    SHIPPING_FEE,
    TAX_RATE,
)

router = APIRouter(prefix="/api/v1/carts", tags=["carts"])


# ---------- 共通の小さな関数 ----------

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def make_line_key(sku_id, status, method_id, inseam_cm) -> str:
    """同じ明細にまとめてよいかを表す文字列（cart_rules.line_key と同じ組み合わせ）。"""
    return f"{sku_id}|{status}|{method_id or '-'}|{inseam_cm if inseam_cm is not None else '-'}"


def require_object(payload: Any) -> dict:
    if not isinstance(payload, dict):
        raise BusinessRuleError(
            422, "VALIDATION_ERROR", "リクエスト本文はJSONオブジェクトで送信してください。"
        )
    return payload


def require_field(payload: dict, field: str, message: str):
    if payload.get(field) is None:
        raise BusinessRuleError(422, "REQUIRED_FIELD_MISSING", message, field)
    return payload[field]


def find_active_cart(connection: Connection, token: str | None):
    """Cookieのトークンから、有効期限内のACTIVEなカートを探す。"""
    if not token:
        return None
    return connection.execute(
        text("""
            SELECT cart_id, expires_at
            FROM carts
            WHERE guest_token_hash = :token_hash
              AND status = 'ACTIVE'
              AND expires_at > :now
        """),
        {"token_hash": hash_token(token), "now": now()},
    ).mappings().first()


def set_cart_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        GUEST_CART_COOKIE,
        token,
        max_age=CART_EXPIRY_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        path="/",
    )


def touch_cart(connection: Connection, cart_id: str) -> None:
    """更新から30日へ期限を延ばす（期限補足）。"""
    connection.execute(
        text("UPDATE carts SET expires_at = :expires_at WHERE cart_id = :cart_id"),
        {"expires_at": now() + timedelta(days=CART_EXPIRY_DAYS), "cart_id": cart_id},
    )


def available_quantity(connection: Connection, sku_id: str) -> int:
    value = connection.execute(
        text("""
            SELECT COALESCE(on_hand_quantity - reserved_quantity, 0)
            FROM inventories WHERE sku_id = :sku_id
        """),
        {"sku_id": sku_id},
    ).scalar()
    return int(value or 0)


def check_stock(connection: Connection, sku_id: str, quantity: int) -> None:
    if quantity > available_quantity(connection, sku_id):
        raise BusinessRuleError(
            409, "OUT_OF_STOCK", "在庫が不足しています。数量を減らしてください。", "quantity"
        )


def read_alteration(payload: dict) -> tuple:
    status = require_field(payload, "alterationStatus", "裾上げの有無を指定してください。")
    return status, payload.get("alterationMethodId"), payload.get("inseamCm")


# ---------- カートの内容を組み立てる ----------

EMPTY_CART = {
    "cartId": None,
    "status": None,
    "expiresAt": None,
    "items": [],
    "subtotal": 0,
    "alterationFeeTotal": 0,
    "shippingFee": 0,
    "taxAmount": 0,
    "totalAmount": 0,
}


def load_cart(connection: Connection, cart_id: str) -> dict:
    cart = connection.execute(
        text("SELECT cart_id, status, expires_at FROM carts WHERE cart_id = :cart_id"),
        {"cart_id": cart_id},
    ).mappings().first()
    rows = connection.execute(
        text("""
            SELECT
                ci.cart_item_id, ci.sku_id, ci.quantity,
                ci.alteration_status, ci.alteration_method_id, ci.inseam_cm,
                s.sku_code, s.color_name, s.size_code, s.selling_price,
                p.product_id, p.product_name,
                m.method_name, m.alteration_fee, m.additional_business_days,
                COALESCE(i.on_hand_quantity - i.reserved_quantity, 0) AS available
            FROM cart_items AS ci
            JOIN skus AS s ON s.sku_id = ci.sku_id
            JOIN products AS p ON p.product_id = s.product_id
            LEFT JOIN alteration_methods AS m
              ON m.alteration_method_id = ci.alteration_method_id
            LEFT JOIN inventories AS i ON i.sku_id = ci.sku_id
            WHERE ci.cart_id = :cart_id
            ORDER BY ci.created_at, ci.cart_item_id
        """),
        {"cart_id": cart_id},
    ).mappings().all()

    items, lines = [], []
    for r in rows:
        fee = int(r["alteration_fee"]) if r["alteration_fee"] is not None else 0
        price = int(r["selling_price"])
        items.append({
            "cartItemId": r["cart_item_id"],
            "skuId": r["sku_id"],
            "skuCode": r["sku_code"],
            "productId": r["product_id"],
            "productName": r["product_name"],
            "colorName": r["color_name"],
            "sizeCode": r["size_code"],
            "unitPrice": price,
            "quantity": int(r["quantity"]),
            "alterationStatus": r["alteration_status"],
            "alterationMethodId": r["alteration_method_id"],
            "alterationMethodName": r["method_name"],
            "alterationFee": fee,
            "additionalBusinessDays": (
                int(r["additional_business_days"])
                if r["additional_business_days"] is not None else 0
            ),
            "inseamCm": r["inseam_cm"],
            "availableQuantity": int(r["available"]),
            "lineTotal": (price + fee) * int(r["quantity"]),
        })
        lines.append(PriceLine(price, int(r["quantity"]), fee))

    totals = calculate_totals(lines, SHIPPING_FEE, TAX_RATE)
    return {
        "cartId": cart["cart_id"],
        "status": cart["status"],
        "expiresAt": cart["expires_at"].isoformat(),
        "items": items,
        "subtotal": totals.subtotal,
        "alterationFeeTotal": totals.alteration_total,
        "shippingFee": totals.shipping_fee,
        "taxAmount": totals.tax_included,
        "totalAmount": totals.total,
    }


def find_own_item(connection: Connection, cart_id: str, item_id: str):
    """自分のカートの明細だけを返す。他人の明細は存在を明かさない（404）。"""
    return connection.execute(
        text("""
            SELECT cart_item_id, sku_id, quantity
            FROM cart_items
            WHERE cart_item_id = :item_id AND cart_id = :cart_id
        """),
        {"item_id": item_id, "cart_id": cart_id},
    ).mappings().first()


def not_found() -> BusinessRuleError:
    return BusinessRuleError(404, "RESOURCE_NOT_FOUND", "対象の明細が見つかりません。")


# ---------- API ----------

@router.get("/current")
def get_current_cart(request: Request) -> dict:
    """C-01 現在のカート。カートがなければ空のカートを返す（正常）。"""
    with engine.connect() as connection:
        cart = find_active_cart(connection, request.cookies.get(GUEST_CART_COOKIE))
        if cart is None:
            return EMPTY_CART
        return load_cart(connection, cart["cart_id"])


@router.post("/current/items")
def add_cart_item(
    request: Request,
    response: Response,
    payload: Any = Body(None),
) -> dict:
    """C-02 明細を追加する。同じSKU・同じ裾上げ指定なら数量を合算する。"""
    payload = require_object(payload)
    sku_id = normalize_uuid(
        require_field(payload, "skuId", "SKUを指定してください。"), "skuId"
    )
    quantity = validate_quantity(payload.get("quantity"))
    status, method_id, inseam_cm = read_alteration(payload)
    selection = validate_alteration(sku_id, status, method_id, inseam_cm)
    key = make_line_key(
        sku_id, selection.alteration_status,
        selection.alteration_method_id, selection.inseam_cm,
    )

    token = request.cookies.get(GUEST_CART_COOKIE)
    with engine.begin() as connection:
        cart = find_active_cart(connection, token)
        if cart is None:
            token = secrets.token_urlsafe(32)
            connection.execute(
                text("""
                    INSERT INTO carts (guest_token_hash, status, expires_at)
                    VALUES (:token_hash, 'ACTIVE', :expires_at)
                """),
                {
                    "token_hash": hash_token(token),
                    "expires_at": now() + timedelta(days=CART_EXPIRY_DAYS),
                },
            )
            cart = find_active_cart(connection, token)
        cart_id = cart["cart_id"]

        existing = connection.execute(
            text("""
                SELECT cart_item_id, quantity FROM cart_items
                WHERE cart_id = :cart_id AND cart_line_key = :key
                FOR UPDATE
            """),
            {"cart_id": cart_id, "key": key},
        ).mappings().first()

        if existing is None:
            check_stock(connection, sku_id, quantity)
            connection.execute(
                text("""
                    INSERT INTO cart_items (
                        cart_id, sku_id, quantity, alteration_status,
                        alteration_method_id, inseam_cm, cart_line_key
                    ) VALUES (
                        :cart_id, :sku_id, :quantity, :status,
                        :method_id, :inseam_cm, :key
                    )
                """),
                {
                    "cart_id": cart_id, "sku_id": sku_id, "quantity": quantity,
                    "status": selection.alteration_status,
                    "method_id": selection.alteration_method_id,
                    "inseam_cm": selection.inseam_cm, "key": key,
                },
            )
        else:
            merged = validate_added_quantity(int(existing["quantity"]), quantity)
            check_stock(connection, sku_id, merged)
            connection.execute(
                text("UPDATE cart_items SET quantity = :q WHERE cart_item_id = :id"),
                {"q": merged, "id": existing["cart_item_id"]},
            )
        touch_cart(connection, cart_id)
        result = load_cart(connection, cart_id)

    set_cart_cookie(response, token)
    return result


@router.patch("/current/items/{cartItemId}")
def update_cart_item(
    cartItemId: str,
    request: Request,
    response: Response,
    payload: Any = Body(None),
) -> dict:
    """C-03 数量と裾上げ指定を変更する。変更後に別の明細と同じ指定になれば合算する。"""
    item_id = normalize_uuid(cartItemId, "cartItemId")
    payload = require_object(payload)
    quantity = validate_quantity(payload.get("quantity"))
    status, method_id, inseam_cm = read_alteration(payload)
    token = request.cookies.get(GUEST_CART_COOKIE)

    with engine.begin() as connection:
        cart = find_active_cart(connection, token)
        if cart is None:
            raise not_found()
        cart_id = cart["cart_id"]
        item = find_own_item(connection, cart_id, item_id)
        if item is None:
            raise not_found()

        selection = validate_alteration(item["sku_id"], status, method_id, inseam_cm)
        key = make_line_key(
            item["sku_id"], selection.alteration_status,
            selection.alteration_method_id, selection.inseam_cm,
        )
        other = connection.execute(
            text("""
                SELECT cart_item_id, quantity FROM cart_items
                WHERE cart_id = :cart_id AND cart_line_key = :key
                  AND cart_item_id <> :item_id
            """),
            {"cart_id": cart_id, "key": key, "item_id": item_id},
        ).mappings().first()

        if other is None:
            check_stock(connection, item["sku_id"], quantity)
            connection.execute(
                text("""
                    UPDATE cart_items
                    SET quantity = :q, alteration_status = :status,
                        alteration_method_id = :method_id, inseam_cm = :inseam_cm,
                        cart_line_key = :key
                    WHERE cart_item_id = :id
                """),
                {
                    "q": quantity, "status": selection.alteration_status,
                    "method_id": selection.alteration_method_id,
                    "inseam_cm": selection.inseam_cm, "key": key, "id": item_id,
                },
            )
        else:
            merged = validate_added_quantity(int(other["quantity"]), quantity)
            check_stock(connection, item["sku_id"], merged)
            connection.execute(
                text("UPDATE cart_items SET quantity = :q WHERE cart_item_id = :id"),
                {"q": merged, "id": other["cart_item_id"]},
            )
            connection.execute(
                text("DELETE FROM cart_items WHERE cart_item_id = :id"),
                {"id": item_id},
            )
        touch_cart(connection, cart_id)
        result = load_cart(connection, cart_id)

    set_cart_cookie(response, token)
    return result


@router.delete("/current/items/{cartItemId}", status_code=204)
def delete_cart_item(cartItemId: str, request: Request) -> Response:
    """C-04 明細を削除する。削除済み・自分のものでない明細も、何も変えずに204を返す。"""
    item_id = normalize_uuid(cartItemId, "cartItemId")
    with engine.begin() as connection:
        cart = find_active_cart(connection, request.cookies.get(GUEST_CART_COOKIE))
        if cart is not None:
            deleted = connection.execute(
                text("""
                    DELETE FROM cart_items
                    WHERE cart_item_id = :id AND cart_id = :cart_id
                """),
                {"id": item_id, "cart_id": cart["cart_id"]},
            )
            if deleted.rowcount:
                touch_cart(connection, cart["cart_id"])
    return Response(status_code=204)
