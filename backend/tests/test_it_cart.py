"""IT-CART-001～006、IT-SEC-001 カートAPIの結合テスト（テスト仕様書 10章・12章）。

FastAPIのアプリへ実際にHTTP要求を送り、MySQLに保存された内容まで確認する。
MySQLが必要なので、環境変数 RUN_IT=1 のときだけ実行する（CIでは自動でスキップ）。
各ケースの前にカート関連のテーブルを空にする。在庫・商品データは変更しない。
"""
import os

import pytest

if os.environ.get("RUN_IT") != "1":
    pytest.skip("結合テストは RUN_IT=1 のときだけ実行する", allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from db import engine  # noqa: E402
from main import app  # noqa: E402

SKU_S = "22222222-2222-4222-8222-222222222221"
SKU_M = "22222222-2222-4222-8222-222222222222"
URL = "/api/v1/carts/current"


@pytest.fixture(autouse=True)
def clean_carts():
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM cart_items"))
        connection.execute(text("DELETE FROM carts"))
    yield


@pytest.fixture(scope="module")
def machine_id():
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT alteration_method_id FROM alteration_methods WHERE method_code = 'MACHINE'")
        ).scalar_one()


def hem(sku, method_id, inseam, quantity=1):
    return {
        "skuId": sku, "quantity": quantity, "alterationStatus": "SELECTED",
        "alterationMethodId": method_id, "inseamCm": inseam,
    }


def plain(sku, quantity=1):
    return {
        "skuId": sku, "quantity": quantity, "alterationStatus": "NONE",
        "alterationMethodId": None, "inseamCm": None,
    }


def saved_items():
    """DBに保存された明細（股下順）。"""
    with engine.connect() as connection:
        return connection.execute(
            text("""
                SELECT sku_id, alteration_status, alteration_method_id,
                       inseam_cm, quantity
                FROM cart_items ORDER BY inseam_cm, sku_id
            """)
        ).mappings().all()


def test_IT_CART_001_S_ミシン74cmを追加して再取得(machine_id):
    client = TestClient(app)
    assert client.post(f"{URL}/items", json=hem(SKU_S, machine_id, 74)).status_code == 200
    cart = client.get(URL).json()
    item = cart["items"][0]
    assert (item["skuId"], item["alterationMethodId"], item["inseamCm"], item["quantity"]) == (
        SKU_S, machine_id, 74, 1
    )
    row = saved_items()[0]
    assert (row["sku_id"], row["alteration_method_id"], row["inseam_cm"], row["quantity"]) == (
        SKU_S, machine_id, 74, 1
    )


def test_IT_CART_002_S_64cmは422で明細不変(machine_id):
    client = TestClient(app)
    client.post(f"{URL}/items", json=hem(SKU_S, machine_id, 74))
    before = saved_items()
    res = client.post(f"{URL}/items", json=hem(SKU_S, machine_id, 64))
    assert res.status_code == 422
    assert res.json()["errorCode"] == "INSEAM_OUT_OF_RANGE"
    assert res.json()["message"] == "股下は65～80cmの整数で指定してください。"
    assert saved_items() == before


def test_IT_CART_003_Mの範囲をDBから参照(machine_id):
    client = TestClient(app)
    res = client.post(f"{URL}/items", json=hem(SKU_M, machine_id, 68))
    assert res.status_code == 422
    assert res.json()["message"] == "股下は70～85cmの整数で指定してください。"
    res = client.post(f"{URL}/items", json=hem(SKU_M, machine_id, 83))
    assert res.status_code == 200
    assert [(r["sku_id"], r["inseam_cm"]) for r in saved_items()] == [(SKU_M, 83)]


def test_IT_CART_004_同じ股下は合算し違う股下は別明細(machine_id):
    client = TestClient(app)
    for inseam in (74, 74, 75):
        assert client.post(f"{URL}/items", json=hem(SKU_S, machine_id, inseam)).status_code == 200
    assert [(r["inseam_cm"], r["quantity"]) for r in saved_items()] == [(74, 2), (75, 1)]


def test_IT_CART_005_合計10点までで11点目は拒否():
    client = TestClient(app)
    client.post(f"{URL}/items", json=plain(SKU_S, 9))
    assert client.post(f"{URL}/items", json=plain(SKU_S, 1)).status_code == 200
    assert saved_items()[0]["quantity"] == 10
    res = client.post(f"{URL}/items", json=plain(SKU_S, 1))
    assert res.status_code == 422
    assert res.json()["errorCode"] == "QUANTITY_OUT_OF_RANGE"
    assert saved_items()[0]["quantity"] == 10


def test_IT_CART_006_1明細を削除し残明細と金額が一致():
    client = TestClient(app)
    client.post(f"{URL}/items", json=plain(SKU_S))
    cart = client.post(f"{URL}/items", json=plain(SKU_M)).json()
    target = next(i for i in cart["items"] if i["skuId"] == SKU_M)
    assert client.delete(f"{URL}/items/{target['cartItemId']}").status_code == 204
    cart = client.get(URL).json()
    assert [i["skuId"] for i in cart["items"]] == [SKU_S]
    # 商品1,000円＋送料500円＝1,500円、内税136円
    assert (cart["subtotal"], cart["shippingFee"], cart["totalAmount"], cart["taxAmount"]) == (
        1000, 500, 1500, 136
    )


def test_IT_SEC_001_他人のカート明細を参照変更削除できない(machine_id):
    owner = TestClient(app)
    other = TestClient(app)
    item_id = owner.post(f"{URL}/items", json=hem(SKU_S, machine_id, 74)).json()["items"][0]["cartItemId"]
    before = saved_items()

    assert other.get(URL).json()["items"] == []
    res = other.patch(f"{URL}/items/{item_id}", json=hem(SKU_S, machine_id, 70, 2))
    assert res.status_code == 404
    assert other.delete(f"{URL}/items/{item_id}").status_code == 204
    assert saved_items() == before
    assert owner.get(URL).json()["items"][0]["cartItemId"] == item_id
