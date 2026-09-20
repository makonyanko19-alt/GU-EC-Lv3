"""購入確認と注文（設計 CK-01・O-01・O-02）。ゲストの購入経路をローカルで動かす範囲。

注文の流れ（設計 11章のトランザクション）
  Tx1  在庫確保、注文・明細・確保・決済試行の作成、カートをCONVERTEDへ
  Tx外 Wallet決済の要求（代役）。応答なしは失敗と断定せずUNKNOWN
  Tx2  成功：注文CONFIRMED・確保CONSUMED・在庫を減らす
       失敗：注文PAYMENT_FAILED・確保RELEASED・確保数を戻す
金額はリクエストの値を使わず、最新のDB値から計算し直す。
"""
import re
import secrets
from datetime import date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Connection

import wallet_mock
from alteration_rules import normalize_uuid
from carts import find_active_cart, hash_token, load_cart, now
from db import engine
from delivery import add_business_days, estimate_delivery_date
from payment_rules import on_inquiry_result, on_payment_timeout
from rule_errors import BusinessRuleError
from settings import (
    GUEST_CART_COOKIE,
    NORMAL_DELIVERY_BUSINESS_DAYS,
    RESERVATION_MINUTES,
    TAX_RATE,
)

router = APIRouter(prefix="/api/v1", tags=["orders"])

GUEST_ORDER_COOKIE = "guestOrderToken"
ORDER_ACCESS_DAYS = 30
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
POSTAL_PATTERN = re.compile(r"^\d{3}-?\d{4}$")
ADDRESS_FIELDS = {
    "recipientName": "お名前",
    "contactEmail": "メールアドレス",
    "postalCode": "郵便番号",
    "prefecture": "都道府県",
    "city": "市区町村",
    "addressLine1": "番地",
    "phoneNumber": "電話番号",
}


# ---------- 入力の確認 ----------

def validate_address(value: Any) -> dict:
    if not isinstance(value, dict):
        raise BusinessRuleError(
            422, "REQUIRED_FIELD_MISSING", "配送先を入力してください。", "deliveryAddress"
        )
    address = {}
    for field, label in ADDRESS_FIELDS.items():
        v = value.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            raise BusinessRuleError(
                422, "REQUIRED_FIELD_MISSING", f"{label}を入力してください。",
                f"deliveryAddress.{field}",
            )
        if not isinstance(v, str):
            raise BusinessRuleError(
                422, "INVALID_INPUT_TYPE", f"{label}は文字列で入力してください。",
                f"deliveryAddress.{field}",
            )
        address[field] = v.strip()
    email = address["contactEmail"].lower()
    if len(email) > 254 or not EMAIL_PATTERN.match(email):
        raise BusinessRuleError(
            422, "INVALID_EMAIL", "メールアドレスの形式が正しくありません。",
            "deliveryAddress.contactEmail",
        )
    address["contactEmail"] = email
    if not POSTAL_PATTERN.match(address["postalCode"]):
        raise BusinessRuleError(
            422, "INVALID_INPUT_TYPE", "郵便番号は7桁の数字で入力してください。",
            "deliveryAddress.postalCode",
        )
    line2 = value.get("addressLine2")
    address["addressLine2"] = line2.strip() if isinstance(line2, str) and line2.strip() else None
    return address


def validate_checkout(payload: Any) -> tuple[str, dict]:
    if not isinstance(payload, dict):
        raise BusinessRuleError(
            422, "VALIDATION_ERROR", "リクエスト本文はJSONオブジェクトで送信してください。"
        )
    cart_id = payload.get("cartId")
    if cart_id is None:
        raise BusinessRuleError(422, "REQUIRED_FIELD_MISSING", "カートを指定してください。", "cartId")
    cart_id = normalize_uuid(cart_id, "cartId")
    address = validate_address(payload.get("deliveryAddress"))
    if payload.get("deliveryMethod") != "HOME_DELIVERY":
        raise BusinessRuleError(
            422, "INVALID_DELIVERY_METHOD", "配送方法は自宅配送のみ選べます。", "deliveryMethod"
        )
    if payload.get("paymentProvider") != "WALLET":
        raise BusinessRuleError(
            422, "PAYMENT_METHOD_UNAVAILABLE", "支払方法はWalletのみ選べます。", "paymentProvider"
        )
    return cart_id, address


def own_cart(connection: Connection, request: Request, cart_id: str) -> dict:
    """Cookieのカートと指定のcartIdが一致するときだけ、その内容を返す。"""
    cart = find_active_cart(connection, request.cookies.get(GUEST_CART_COOKIE))
    if cart is None or cart["cart_id"] != cart_id:
        raise BusinessRuleError(404, "CART_NOT_FOUND", "カートが見つかりません。", "cartId")
    content = load_cart(connection, cart_id)
    if not content["items"]:
        raise BusinessRuleError(422, "EMPTY_CART", "カートに商品がありません。")
    return content


def delivery_date_for(content: dict, today: date | None = None) -> date:
    """通常配送（翌営業日から2営業日）に、裾上げがあれば3営業日を1回加算する。"""
    today = today or date.today()
    normal = add_business_days(today, NORMAL_DELIVERY_BUSINESS_DAYS, set())
    flags = [i["alterationStatus"] == "SELECTED" for i in content["items"]]
    return estimate_delivery_date(normal, flags, set())


def stock_shortages(content: dict) -> list[dict]:
    return [
        {
            "skuId": i["skuId"],
            "requestedQuantity": i["quantity"],
            "availableQuantity": i["availableQuantity"],
        }
        for i in content["items"]
        if i["quantity"] > i["availableQuantity"]
    ]


def money(content: dict) -> dict:
    return {k: content[k] for k in (
        "subtotal", "alterationFeeTotal", "shippingFee", "taxAmount", "totalAmount"
    )}


# ---------- CK-01 購入確認 ----------

@router.post("/checkout/preview")
def checkout_preview(request: Request, payload: Any = Body(None)) -> dict:
    """最新の金額・配送予定日・在庫不足を返す。DBは更新しない。"""
    cart_id, _ = validate_checkout(payload)
    with engine.connect() as connection:
        content = own_cart(connection, request, cart_id)
    return {
        **money(content),
        "estimatedDeliveryDate": delivery_date_for(content).isoformat(),
        "stockShortages": stock_shortages(content),
    }


# ---------- O-01 注文 ----------

def new_order_number() -> str:
    return f"GU{datetime.now():%Y%m%d}-{secrets.randbelow(10**6):06d}"


def create_order_tx1(
    connection: Connection, content: dict, address: dict, access_hash: str
) -> dict:
    """Tx1：在庫を確保し、注文・明細・確保・決済試行を作り、カートを変換済みにする。"""
    # 在庫行をロックしてから確保する（同時注文で在庫が負にならないように）。
    for item in content["items"]:
        stock = connection.execute(
            text("""
                SELECT on_hand_quantity, reserved_quantity
                FROM inventories WHERE sku_id = :sku_id FOR UPDATE
            """),
            {"sku_id": item["skuId"]},
        ).mappings().first()
        available = 0 if stock is None else stock["on_hand_quantity"] - stock["reserved_quantity"]
        if item["quantity"] > available:
            raise BusinessRuleError(
                409, "OUT_OF_STOCK", "在庫が不足している商品があります。数量を見直してください。"
            )
        connection.execute(
            text("""
                UPDATE inventories SET reserved_quantity = reserved_quantity + :q
                WHERE sku_id = :sku_id
            """),
            {"q": item["quantity"], "sku_id": item["skuId"]},
        )

    order_id = connection.execute(text("SELECT UUID()")).scalar()
    order_number = new_order_number()
    delivery = delivery_date_for(content)
    connection.execute(
        text("""
            INSERT INTO orders (
                order_id, order_number, source_cart_id, guest_access_token_hash, status,
                subtotal, alteration_fee_total, shipping_fee, tax_rate, tax_amount, total_amount,
                recipient_name, contact_email, postal_code, prefecture, city,
                address_line1, address_line2, phone_number,
                delivery_method, estimated_delivery_date
            ) VALUES (
                :order_id, :order_number, :cart_id, :access_hash, 'PAYMENT_PENDING',
                :subtotal, :alteration, :shipping, :tax_rate, :tax, :total,
                :recipientName, :contactEmail, :postalCode, :prefecture, :city,
                :addressLine1, :addressLine2, :phoneNumber,
                'HOME_DELIVERY', :delivery
            )
        """),
        {
            "order_id": order_id, "order_number": order_number,
            "cart_id": content["cartId"], "access_hash": access_hash,
            "subtotal": content["subtotal"], "alteration": content["alterationFeeTotal"],
            "shipping": content["shippingFee"], "tax_rate": TAX_RATE,
            "tax": content["taxAmount"], "total": content["totalAmount"],
            "delivery": delivery, **address,
        },
    )
    expires_at = now() + timedelta(minutes=RESERVATION_MINUTES)
    for item in content["items"]:
        item_id = connection.execute(text("SELECT UUID()")).scalar()
        connection.execute(
            text("""
                INSERT INTO order_items (
                    order_item_id, order_id, product_id, sku_id, product_name, sku_code,
                    color_name, size_code, unit_price, quantity, alteration_status,
                    alteration_method_id, alteration_method_name, alteration_fee,
                    inseam_cm, line_total
                ) VALUES (
                    :item_id, :order_id, :productId, :skuId, :productName, :skuCode,
                    :colorName, :sizeCode, :unitPrice, :quantity, :alterationStatus,
                    :alterationMethodId, :alterationMethodName, :alterationFee,
                    :inseamCm, :lineTotal
                )
            """),
            {"item_id": item_id, "order_id": order_id, **item},
        )
        connection.execute(
            text("""
                INSERT INTO stock_reservations
                    (order_item_id, sku_id, quantity, status, expires_at)
                VALUES (:item_id, :sku_id, :q, 'RESERVED', :expires_at)
            """),
            {"item_id": item_id, "sku_id": item["skuId"], "q": item["quantity"],
             "expires_at": expires_at},
        )
    connection.execute(
        text("""
            INSERT INTO payments (order_id, attempt_no, provider, amount, status)
            VALUES (:order_id, 1, 'WALLET', :amount, 'REQUESTED')
        """),
        {"order_id": order_id, "amount": content["totalAmount"]},
    )
    connection.execute(
        text("UPDATE carts SET status = 'CONVERTED' WHERE cart_id = :cart_id"),
        {"cart_id": content["cartId"]},
    )
    return {"order_id": order_id, "order_number": order_number}


def finish_payment_tx2(
    connection: Connection, order_id: str, status: str, transaction_id: str | None
) -> None:
    """Tx2：決済の確定結果を注文・確保・在庫へ反映する。"""
    decision = on_inquiry_result(status)
    connection.execute(
        text("""
            UPDATE payments SET status = :status, provider_transaction_id = :tx
            WHERE order_id = :order_id AND attempt_no = 1
        """),
        {"status": decision.payment_status, "tx": transaction_id, "order_id": order_id},
    )
    confirmed_at = now() if decision.confirm_order else None
    connection.execute(
        text("""
            UPDATE orders SET status = :status, confirmed_at = :confirmed_at,
                access_expires_at = :access_expires_at
            WHERE order_id = :order_id
        """),
        {
            "status": decision.order_status, "confirmed_at": confirmed_at,
            "access_expires_at": (
                confirmed_at + timedelta(days=ORDER_ACCESS_DAYS) if confirmed_at else None
            ),
            "order_id": order_id,
        },
    )
    if decision.consume_inventory or decision.release_reservation:
        reservations = connection.execute(
            text("""
                SELECT r.reservation_id, r.sku_id, r.quantity
                FROM stock_reservations AS r
                JOIN order_items AS oi ON oi.order_item_id = r.order_item_id
                WHERE oi.order_id = :order_id AND r.status = 'RESERVED'
                FOR UPDATE
            """),
            {"order_id": order_id},
        ).mappings().all()
        for r in reservations:
            if decision.consume_inventory:
                connection.execute(
                    text("""
                        UPDATE inventories
                        SET on_hand_quantity = on_hand_quantity - :q,
                            reserved_quantity = reserved_quantity - :q
                        WHERE sku_id = :sku_id
                    """),
                    {"q": r["quantity"], "sku_id": r["sku_id"]},
                )
                new_status = "CONSUMED"
            else:
                connection.execute(
                    text("""
                        UPDATE inventories SET reserved_quantity = reserved_quantity - :q
                        WHERE sku_id = :sku_id
                    """),
                    {"q": r["quantity"], "sku_id": r["sku_id"]},
                )
                new_status = "RELEASED"
            connection.execute(
                text("UPDATE stock_reservations SET status = :s WHERE reservation_id = :id"),
                {"s": new_status, "id": r["reservation_id"]},
            )


def mark_unknown(connection: Connection, order_id: str) -> None:
    """応答なし：決済はUNKNOWN、注文はPAYMENT_PENDINGのまま。確保は維持する。"""
    decision = on_payment_timeout()
    connection.execute(
        text("UPDATE payments SET status = :s WHERE order_id = :order_id AND attempt_no = 1"),
        {"s": decision.payment_status, "order_id": order_id},
    )


@router.post("/orders")
def create_order(request: Request, payload: Any = Body(None)) -> JSONResponse:
    """注文を作り、Walletへ決済を要求する。成功201、結果不明202、失敗は201でPAYMENT_FAILED。"""
    cart_id, address = validate_checkout(payload)
    expected = payload.get("expectedTotalAmount")
    if expected is None:
        raise BusinessRuleError(
            422, "REQUIRED_FIELD_MISSING", "確認した合計金額を指定してください。",
            "expectedTotalAmount",
        )
    if isinstance(expected, bool) or not isinstance(expected, int):
        raise BusinessRuleError(
            422, "INVALID_INPUT_TYPE", "確認した合計金額は整数で指定してください。",
            "expectedTotalAmount",
        )

    access_token = secrets.token_urlsafe(32)
    with engine.begin() as connection:
        content = own_cart(connection, request, cart_id)
        # 確認画面の後に金額が変わっていたら、注文も確保も作らずに再確認を求める。
        if content["totalAmount"] != expected:
            raise BusinessRuleError(
                409, "PRICE_CHANGED",
                "価格または補正料が変更されました。最新の金額を確認してください。",
            )
        created = create_order_tx1(connection, content, address, hash_token(access_token))

    try:
        wallet_result = wallet_mock.request_payment(
            created["order_number"], content["totalAmount"]
        )
    except wallet_mock.WalletTimeout:
        with engine.begin() as connection:
            mark_unknown(connection, created["order_id"])
    else:
        with engine.begin() as connection:
            finish_payment_tx2(
                connection, created["order_id"],
                wallet_result["status"], wallet_result["transactionId"],
            )

    body = get_order_body(created["order_id"])
    status_code = 202 if body["paymentStatus"] == "UNKNOWN" else 201
    result = JSONResponse(status_code=status_code, content=body)
    # 注文照会用のCookie。注文確定から30日で、カートの更新では延長しない。
    result.set_cookie(
        GUEST_ORDER_COOKIE, access_token, max_age=ORDER_ACCESS_DAYS * 24 * 60 * 60,
        httponly=True, samesite="lax", path="/",
    )
    return result


# ---------- O-02 注文照会 ----------

def next_action(order_status: str, payment_status: str) -> str:
    if payment_status == "UNKNOWN":
        return "WAIT_PAYMENT_RESULT"
    if order_status == "PAYMENT_FAILED":
        return "RETRY_PAYMENT"
    return "NONE"


def get_order_body(order_id: str) -> dict:
    with engine.connect() as connection:
        order = connection.execute(
            text("SELECT * FROM orders WHERE order_id = :id"), {"id": order_id}
        ).mappings().first()
        items = connection.execute(
            text("SELECT * FROM order_items WHERE order_id = :id ORDER BY order_item_id"),
            {"id": order_id},
        ).mappings().all()
        payments = connection.execute(
            text("""
                SELECT attempt_no, status, amount, created_at
                FROM payments WHERE order_id = :id ORDER BY attempt_no
            """),
            {"id": order_id},
        ).mappings().all()
    payment_status = payments[-1]["status"] if payments else None
    return {
        "orderId": order["order_id"],
        "orderNumber": order["order_number"],
        "orderStatus": order["status"],
        "paymentStatus": payment_status,
        "nextAction": next_action(order["status"], payment_status),
        "subtotal": int(order["subtotal"]),
        "alterationFeeTotal": int(order["alteration_fee_total"]),
        "shippingFee": int(order["shipping_fee"]),
        "taxAmount": int(order["tax_amount"]),
        "totalAmount": int(order["total_amount"]),
        "estimatedDeliveryDate": order["estimated_delivery_date"].isoformat(),
        "items": [
            {
                "productName": i["product_name"], "skuId": i["sku_id"],
                "colorName": i["color_name"], "sizeCode": i["size_code"],
                "unitPrice": int(i["unit_price"]), "quantity": i["quantity"],
                "alterationStatus": i["alteration_status"],
                "alterationMethodName": i["alteration_method_name"],
                "alterationFee": int(i["alteration_fee"]), "inseamCm": i["inseam_cm"],
                "lineTotal": int(i["line_total"]),
            }
            for i in items
        ],
        "payments": [
            {"attemptNo": p["attempt_no"], "status": p["status"], "amount": int(p["amount"])}
            for p in payments
        ],
    }


@router.get("/orders/{orderId}")
def get_order(orderId: str, request: Request) -> dict:
    """本人の注文だけを返す。他人の注文・期限切れは存在を明かさず404。"""
    order_id = normalize_uuid(orderId, "orderId")
    token = request.cookies.get(GUEST_ORDER_COOKIE)
    with engine.connect() as connection:
        row = connection.execute(
            text("""
                SELECT order_id FROM orders
                WHERE order_id = :id AND guest_access_token_hash = :hash
                  AND (access_expires_at IS NULL OR access_expires_at > :now)
            """),
            {"id": order_id, "hash": hash_token(token) if token else "", "now": now()},
        ).first()
    if row is None:
        raise BusinessRuleError(404, "ORDER_NOT_FOUND", "注文が見つかりません。")
    return get_order_body(order_id)
