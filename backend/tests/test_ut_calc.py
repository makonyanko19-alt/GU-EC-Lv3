"""UT-CALC-001～009、UT-TAX-001～002 金額と税率の単体テスト（テスト仕様書 5章）。

期待値は仕様書のケース表の値をそのまま使う（関数で期待値を作らない）。
"""
import pytest

from pricing import PriceLine, calculate_totals, validate_tax_rate
from rule_errors import BusinessRuleError

SHIPPING = 500
MACHINE_FEE = 300
CHAIN_FEE = 560


def test_UT_CALC_001_D01の合計と内税():
    # D-01：商品A・B各1,007円、各1点、補正なし、送料500円、税率10％
    lines = [PriceLine(1007, 1), PriceLine(1007, 1)]
    t = calculate_totals(lines, SHIPPING, 10)
    assert (t.subtotal, t.alteration_total, t.shipping_fee) == (2014, 0, 500)
    assert (t.total, t.tax_included, t.total_excluding_tax) == (2514, 228, 2286)


@pytest.mark.parametrize(
    ("total", "expected_tax"),
    [(1099, 99), (1100, 100), (1101, 100)],
    ids=["a_1099", "b_1100", "c_1101"],
)
def test_UT_CALC_002_内税の切り捨て境界(total, expected_tax):
    # 送料0円・1明細で、税込合計がそのまま total になるようにする。
    t = calculate_totals([PriceLine(total, 1)], 0, 10)
    assert t.total == total
    assert t.tax_included == expected_tax


@pytest.mark.parametrize(
    "lines",
    [[PriceLine(1007, 2)], [PriceLine(1007, 1), PriceLine(1007, 1)]],
    ids=["a_one_line", "b_two_lines"],
)
def test_UT_CALC_003_明細の分け方で結果が変わらない(lines):
    t = calculate_totals(lines, SHIPPING, 10)
    assert (t.total, t.tax_included) == (2514, 228)


def test_UT_CALC_004_ミシン1点():
    t = calculate_totals([PriceLine(1000, 1, MACHINE_FEE)], SHIPPING, 10)
    assert (t.alteration_total, t.total, t.tax_included) == (300, 1800, 163)


def test_UT_CALC_005_チェーン1点():
    t = calculate_totals([PriceLine(1000, 1, CHAIN_FEE)], SHIPPING, 10)
    assert (t.alteration_total, t.total, t.tax_included) == (560, 2060, 187)


def test_UT_CALC_006_ミシン1点と補正なし1点():
    lines = [PriceLine(1000, 1, MACHINE_FEE), PriceLine(1000, 1)]
    t = calculate_totals(lines, SHIPPING, 10)
    assert (t.alteration_total, t.total, t.tax_included) == (300, 2800, 254)


@pytest.mark.parametrize(
    ("fee", "expected"),
    [(MACHINE_FEE, (600, 3100, 281)), (CHAIN_FEE, (1120, 3620, 329))],
    ids=["a_machine", "b_chain"],
)
def test_UT_CALC_007_同じ股下で2点(fee, expected):
    t = calculate_totals([PriceLine(1000, 2, fee)], SHIPPING, 10)
    assert (t.alteration_total, t.total, t.tax_included) == expected


@pytest.mark.parametrize(
    ("rate", "expected_tax"),
    [(10, 228), (8, 186), (0, 0)],
    ids=["a_10", "b_8", "c_0"],
)
def test_UT_CALC_008_税率別の内税と合計不変(rate, expected_tax):
    t = calculate_totals([PriceLine(2514, 1)], 0, rate)
    assert t.total == 2514
    assert t.tax_included == expected_tax


def test_UT_CALC_009_空明細はすべて0円():
    t = calculate_totals([], SHIPPING, 10)
    assert (
        t.subtotal, t.alteration_total, t.shipping_fee, t.total, t.tax_included
    ) == (0, 0, 0, 0, 0)


@pytest.mark.parametrize(
    ("rate", "accepted"),
    [(-1, False), (0, True), (1, True), (98, True), (99, True), (100, False)],
    ids=["a_-1", "b_0", "c_1", "d_98", "e_99", "f_100"],
)
def test_UT_TAX_001_税率の境界(rate, accepted):
    if accepted:
        assert validate_tax_rate(rate) == rate
    else:
        with pytest.raises(BusinessRuleError) as error:
            validate_tax_rate(rate)
        assert error.value.error_code == "INVALID_TAX_RATE"


@pytest.mark.parametrize(
    "rate",
    [None, "", "10", 10.0, True],
    ids=["a_null", "b_empty", "c_str_10", "d_float_10.0", "e_bool"],
)
def test_UT_TAX_002_不正な型の税率を拒否(rate):
    with pytest.raises(BusinessRuleError) as error:
        validate_tax_rate(rate)
    assert error.value.error_code == "INVALID_TAX_RATE"
