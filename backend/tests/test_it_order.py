"""購入確認・注文・決済の結合テスト（テスト仕様書 11章・12章）。

対象：IT-ORD-001・002・004・005、IT-SNAP-001、IT-PAY-001・002、IT-SEC-002（ゲスト）
Wallet決済は代役（wallet_mock）。環境変数 WALLET_MOCK_RESULT で結果を切り替える。
MySQLが必要なので、環境変数 RUN_IT=1 のときだけ実行する（CIでは自動でスキップ）。
各ケースの前後で、注文・カートを空にし、確認用データの在庫と価格を初期値へ戻す。
"""
import os
import threading

import pytest

if os.environ.get("RUN_IT") != "1":
    pytest.skip("結合テストは RUN_IT=1 のときだけ実行する", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

import wallet_mock  # noqa: E402
from db import engine  # noqa: E402
from main import app  # noqa: E402

SKU_S = "22222222-2222-4222-8222-222222222221"
SKU_M = "22222222-2222-4222-8222-222222222222"
# テスト専用の商品（D-01の商品A・B、在庫1の商品C）。テスト後に削除する。
TEST_PRODUCT = "99999999-0000-4000-8000-000000000001"
SKU_A = "99999999-0000-4000-8000-00000000000a"
SKU_B = "99999999-0000-4000-8000-00000000000b"
SKU_C = "99999999-0000-4000-8000-00000000000c"

ADDRESS = {
    "recipientName": "テスト 太郎", "contactEmail": "Test@Example.com",
    "postalCode": "100-0001", "prefecture": "東京都", "city": "千代田区",
    "addressLine1": "千代田1-1", "phoneNumber": "0312345678",
}


def run_sql(sql, params=None):
    with engine.begin() as connection:
        connection.execute(text(sql), params or {})


def count(table):
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


def stock(sku):
    with engine.connect() as connection:
        return tuple(connection.execute(
            text("SELECT on_hand_quantity, reserved_quantity FROM inventories WHERE sku_id = :s"),
            {"s": sku},
        ).one())


def clean():
    for sql in (
        "DELETE FROM payments", "DELETE FROM stock_reservations",
        "DELETE FROM order_items", "DELETE FROM orders",
        "DELETE FROM cart_items", "DELETE FROM carts",
        "DELETE FROM inventories WHERE sku_id IN (:a, :b, :c)",
        "DELETE FROM skus WHERE product_id = :p",
        "DELETE FROM products WHERE product_id = :p",
    ):
        run_sql(sql, {"a": SKU_A, "b": SKU_B, "c": SKU_C, "p": TEST_PRODUCT})
    # 確認用データ（003）の在庫・価格・補正料を初期値へ戻す。
    run_sql("UPDATE inventories SET on_hand_quantity = 10, reserved_quantity = 0 WHERE sku_id = :s", {"s": SKU_S})
    run_sql("UPDATE inventories SET on_hand_quantity = 20, reserved_quantity = 0 WHERE sku_id = :s", {"s": SKU_M})
    run_sql("UPDATE skus SET selling_price = 1000 WHERE sku_id IN (:s, :m)", {"s": SKU_S, "m": SKU_M})
    run_sql("UPDATE alteration_methods SET alteration_fee = 300 WHERE method_code = 'MACHINE'")


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    clean()
    wallet_mock.requests_log.clear()
    monkeypatch.setenv("WALLET_MOCK_RESULT", "SUCCEEDED")
    run_sql("""
        INSERT INTO products (product_id, product_code, product_name, is_published)
        VALUES (:p, 'TEST-IT-001', '結合テスト用商品', TRUE)
    """, {"p": TEST_PRODUCT})
    for sku, code, color, price, qty in (
        (SKU_A, "TEST-IT-A", "A", 1007, 10),
        (SKU_B, "TEST-IT-B", "B", 1007, 10),
        (SKU_C, "TEST-IT-C", "C", 1000, 1),
    ):
        run_sql("""
            INSERT INTO skus (sku_id, product_id, sku_code, color_code, color_name,
                              size_code, selling_price, is_active)
            VALUES (:sku, :p, :code, :color, :color, 'F', :price, TRUE)
        """, {"sku": sku, "p": TEST_PRODUCT, "code": code, "color": color, "price": price})
        run_sql("INSERT INTO inventories (sku_id, on_hand_quantity) VALUES (:sku, :q)",
                {"sku": sku, "q": qty})
    yield
    clean()


@pytest.fixture(scope="module")
def machine_id():
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT alteration_method_id FROM alteration_methods WHERE method_code = 'MACHINE'")
        ).scalar_one()


def plain(sku, quantity=1):
    return {"skuId": sku, "quantity": quantity, "alterationStatus": "NONE",
            "alterationMethodId": None, "inseamCm": None}


def checkout_body(cart, **extra):
    return {"cartId": cart["cartId"], "deliveryAddress": ADDRESS,
            "deliveryMethod": "HOME_DELIVERY", "paymentProvider": "WALLET", **extra}


def cart_with(client, *items):
    cart = None
    for item in items:
        res = client.post("/api/v1/carts/current/items", json=item)
        assert res.status_code == 200, res.json()
        cart = res.json()
    return cart


def order(client, cart, expected=None):
    preview = client.post("/api/v1/checkout/preview", json=checkout_body(cart)).json()
    total = preview["totalAmount"] if expected is None else expected
    return client.post("/api/v1/orders", json=checkout_body(cart, expectedTotalAmount=total))


def test_IT_ORD_001_D01で決済成功し確定():
    client = TestClient(app)
    cart = cart_with(client, plain(SKU_A), plain(SKU_B))
    res = order(client, cart)
    assert res.status_code == 201
    body = res.json()
    assert (body["orderStatus"], body["paymentStatus"]) == ("CONFIRMED", "SUCCEEDED")
    with engine.connect() as connection:
        saved = connection.execute(text("SELECT total_amount, tax_amount FROM orders")).one()
    assert (int(saved[0]), int(saved[1])) == (2514, 228)
    assert [r["amount"] for r in wallet_mock.requests_log] == [2514]
    assert stock(SKU_A) == (9, 0) and stock(SKU_B) == (9, 0)


def test_IT_ORD_002_確認後の価格変更は409():
    client = TestClient(app)
    cart = cart_with(client, plain(SKU_S))
    preview = client.post("/api/v1/checkout/preview", json=checkout_body(cart)).json()
    run_sql("UPDATE skus SET selling_price = 1100 WHERE sku_id = :s", {"s": SKU_S})
    res = client.post("/api/v1/orders",
                      json=checkout_body(cart, expectedTotalAmount=preview["totalAmount"]))
    assert res.status_code == 409
    assert res.json()["errorCode"] == "PRICE_CHANGED"
    assert (count("orders"), count("stock_reservations"), count("payments")) == (0, 0, 0)
    assert wallet_mock.requests_log == []
    assert stock(SKU_S) == (10, 0)


def test_IT_ORD_004_在庫1へ同時注文で1件だけ確定():
    clients = [TestClient(app), TestClient(app)]
    carts = [cart_with(c, plain(SKU_C)) for c in clients]
    bodies = [checkout_body(cart, expectedTotalAmount=1500) for cart in carts]
    barrier = threading.Barrier(2)
    results = [None, None]

    def buy(i):
        barrier.wait()  # 同期点：2つの注文を同時に始める
        results[i] = clients[i].post("/api/v1/orders", json=bodies[i])

    threads = [threading.Thread(target=buy, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    codes = sorted(r.status_code for r in results)
    assert codes == [201, 409]
    loser = next(r for r in results if r.status_code == 409)
    assert loser.json()["errorCode"] == "OUT_OF_STOCK"
    assert count("orders") == 1
    assert len(wallet_mock.requests_log) == 1
    assert stock(SKU_C) == (0, 0)


def test_IT_ORD_005_空カートの注文は422():
    client = TestClient(app)
    cart = cart_with(client, plain(SKU_S))
    client.delete(f"/api/v1/carts/current/items/{cart['items'][0]['cartItemId']}")
    res = client.post("/api/v1/orders", json=checkout_body(cart, expectedTotalAmount=0))
    assert res.status_code == 422
    assert res.json()["errorCode"] == "EMPTY_CART"
    assert (count("orders"), count("stock_reservations"), count("payments")) == (0, 0, 0)
    assert wallet_mock.requests_log == []


def test_IT_SNAP_001_確定後の価格変更で注文は不変(machine_id):
    client = TestClient(app)
    cart = cart_with(client, {"skuId": SKU_S, "quantity": 1, "alterationStatus": "SELECTED",
                              "alterationMethodId": machine_id, "inseamCm": 74})
    order_id = order(client, cart).json()["orderId"]
    run_sql("UPDATE skus SET selling_price = 1200 WHERE sku_id = :s", {"s": SKU_S})
    run_sql("UPDATE alteration_methods SET alteration_fee = 400 WHERE method_code = 'MACHINE'")
    body = client.get(f"/api/v1/orders/{order_id}").json()
    item = body["items"][0]
    assert (item["unitPrice"], item["alterationFee"], item["inseamCm"]) == (1000, 300, 74)
    assert (body["totalAmount"], body["taxAmount"]) == (1800, 163)


def test_IT_PAY_001_明確な失敗で未確定と確保解放(monkeypatch):
    monkeypatch.setenv("WALLET_MOCK_RESULT", "FAILED")
    client = TestClient(app)
    res = order(client, cart_with(client, plain(SKU_S)))
    body = res.json()
    assert (body["orderStatus"], body["paymentStatus"]) == ("PAYMENT_FAILED", "FAILED")
    assert body["nextAction"] == "RETRY_PAYMENT"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT status FROM stock_reservations")).scalar() == "RELEASED"
    assert stock(SKU_S) == (10, 0)


def test_IT_PAY_002_応答なしは202とUNKNOWNで確保維持(monkeypatch):
    monkeypatch.setenv("WALLET_MOCK_RESULT", "TIMEOUT")
    client = TestClient(app)
    res = order(client, cart_with(client, plain(SKU_S)))
    assert res.status_code == 202
    body = res.json()
    assert (body["orderStatus"], body["paymentStatus"]) == ("PAYMENT_PENDING", "UNKNOWN")
    assert body["nextAction"] == "WAIT_PAYMENT_RESULT"
    assert count("payments") == 1
    assert stock(SKU_S) == (10, 1)


def test_IT_SEC_002_他人の注文は返さない():
    owner, other = TestClient(app), TestClient(app)
    order_id = order(owner, cart_with(owner, plain(SKU_S))).json()["orderId"]
    assert owner.get(f"/api/v1/orders/{order_id}").status_code == 200
    res = other.get(f"/api/v1/orders/{order_id}")
    assert res.status_code == 404
    assert "orderNumber" not in res.json()
