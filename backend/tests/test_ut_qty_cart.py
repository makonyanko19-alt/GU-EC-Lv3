"""UT-QTY-001～004、UT-CART-001～002 数量と明細の単体テスト（テスト仕様書 7章）。"""
import pytest

from cart_rules import line_key, validate_added_quantity, validate_quantity
from rule_errors import BusinessRuleError

SKU = "22222222-2222-4222-8222-222222222221"
MACHINE_ID = "33333333-3333-4333-8333-333333333331"


def error_code_of(func, *args):
    with pytest.raises(BusinessRuleError) as error:
        func(*args)
    assert error.value.status_code == 422
    return error.value.error_code


def test_UT_QTY_001_数量0は拒否():
    assert error_code_of(validate_quantity, 0) == "QUANTITY_OUT_OF_RANGE"


@pytest.mark.parametrize("quantity", [1, 2], ids=["b_1", "c_2"])
def test_UT_QTY_001_数量1と2は許可(quantity):
    assert validate_quantity(quantity) == quantity


@pytest.mark.parametrize("quantity", [9, 10], ids=["a_9", "b_10"])
def test_UT_QTY_002_数量9と10は許可(quantity):
    assert validate_quantity(quantity) == quantity


def test_UT_QTY_002_数量11は拒否():
    assert error_code_of(validate_quantity, 11) == "QUANTITY_OUT_OF_RANGE"


@pytest.mark.parametrize(
    ("quantity", "expected"),
    [(1.5, "INVALID_INPUT_TYPE"), (None, "REQUIRED_FIELD_MISSING"), ("abc", "INVALID_INPUT_TYPE")],
    ids=["a_1.5", "b_null", "c_abc"],
)
def test_UT_QTY_003_不正な数量を拒否(quantity, expected):
    assert error_code_of(validate_quantity, quantity) == expected


def test_UT_QTY_004_現在9に1追加は合算10で許可():
    assert validate_added_quantity(9, 1) == 10


def test_UT_QTY_004_現在10に1追加は拒否():
    assert error_code_of(validate_added_quantity, 10, 1) == "QUANTITY_OUT_OF_RANGE"


def test_UT_CART_001_同じ股下は合算対象():
    assert line_key(SKU, "SELECTED", MACHINE_ID, 74) == line_key(SKU, "SELECTED", MACHINE_ID, 74)


def test_UT_CART_001_股下が違えば別明細():
    assert line_key(SKU, "SELECTED", MACHINE_ID, 74) != line_key(SKU, "SELECTED", MACHINE_ID, 75)


def test_UT_CART_002_補正ありとなしは別明細():
    assert line_key(SKU, "SELECTED", MACHINE_ID, 74) != line_key(SKU, "NONE", None, None)
