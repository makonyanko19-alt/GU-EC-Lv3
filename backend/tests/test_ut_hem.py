"""UT-HEM-001～010 裾上げ入力の単体テスト（テスト仕様書 6章）。

DBを使わず、判定ルール（alteration_rules.py）だけを確認する。
DBから条件を取得する連携は IT-CART-001～003 で確認する。
"""
import pytest

from alteration_rules import (
    AlterationError,
    check_alteration_input,
    check_alteration_rule,
)

# テスト用の仕上げ方法（IDは固定の架空値）
MACHINE_ID = "33333333-3333-4333-8333-333333333331"
CHAIN_ID = "33333333-3333-4333-8333-333333333332"
MACHINE = {"alteration_fee": 300, "additional_business_days": 3}
CHAIN = {"alteration_fee": 560, "additional_business_days": 3}

# D-02 サイズS：65～80cm、1cm刻み／D-03 サイズM：70～85cm
RULE_S = {
    "is_alteration_available": True,
    "min_inseam_cm": 65,
    "max_inseam_cm": 80,
    "inseam_step_cm": 1,
}
RULE_M = {**RULE_S, "min_inseam_cm": 70, "max_inseam_cm": 85}
RULE_NOT_AVAILABLE = {
    "is_alteration_available": False,
    "min_inseam_cm": None,
    "max_inseam_cm": None,
    "inseam_step_cm": 1,
}


def run(status, method_id, inseam_cm, rule=RULE_S, method=MACHINE):
    """APIと同じ順に、入力チェック → 条件との照合を行う。"""
    normalized_id = check_alteration_input(status, method_id, inseam_cm)
    if status == "NONE":
        return None
    return check_alteration_rule(normalized_id, inseam_cm, rule, method)


def error_code_of(status, method_id, inseam_cm, rule=RULE_S, method=MACHINE):
    """拒否されることを確認し、原因コードを返す。"""
    with pytest.raises(AlterationError) as error:
        run(status, method_id, inseam_cm, rule, method)
    assert error.value.status_code == 422
    return error.value.error_code


def test_UT_HEM_001_裾上げなしは許可():
    assert check_alteration_input("NONE", None, None) is None


@pytest.mark.parametrize(
    ("method_id", "method", "fee"),
    [(MACHINE_ID, MACHINE, 300), (CHAIN_ID, CHAIN, 560)],
    ids=["a_machine", "b_chain"],
)
def test_UT_HEM_002_両方法とも74cmを許可(method_id, method, fee):
    result = run("SELECTED", method_id, 74, method=method)
    assert result.alteration_method_id == method_id
    assert result.inseam_cm == 74
    assert result.alteration_fee == fee


@pytest.mark.parametrize(
    ("status", "method_id", "inseam_cm", "expected"),
    [
        ("NONE", MACHINE_ID, 74, "INVALID_ALTERATION_COMBINATION"),
        ("SELECTED", None, 74, "ALTERATION_INPUT_REQUIRED"),
        ("SELECTED", MACHINE_ID, None, "ALTERATION_INPUT_REQUIRED"),
    ],
    ids=["a_none_with_input", "b_no_method", "c_no_inseam"],
)
def test_UT_HEM_003_状態と入力の不整合を拒否(status, method_id, inseam_cm, expected):
    assert error_code_of(status, method_id, inseam_cm) == expected


def test_UT_HEM_004_下限64は拒否():
    assert error_code_of("SELECTED", MACHINE_ID, 64) == "INSEAM_OUT_OF_RANGE"


@pytest.mark.parametrize("inseam_cm", [65, 66], ids=["b_65", "c_66"])
def test_UT_HEM_004_下限65と66は許可(inseam_cm):
    assert run("SELECTED", MACHINE_ID, inseam_cm).inseam_cm == inseam_cm


@pytest.mark.parametrize("inseam_cm", [79, 80], ids=["a_79", "b_80"])
def test_UT_HEM_005_上限79と80は許可(inseam_cm):
    assert run("SELECTED", MACHINE_ID, inseam_cm).inseam_cm == inseam_cm


def test_UT_HEM_005_上限81は拒否():
    assert error_code_of("SELECTED", MACHINE_ID, 81) == "INSEAM_OUT_OF_RANGE"


@pytest.mark.parametrize("inseam_cm", [74.5, "abc"], ids=["a_74.5", "b_abc"])
def test_UT_HEM_006_整数でない股下を拒否(inseam_cm):
    assert error_code_of("SELECTED", MACHINE_ID, inseam_cm) == "INVALID_INPUT_TYPE"


@pytest.mark.parametrize("inseam_cm", [-1, 0], ids=["a_-1", "b_0"])
def test_UT_HEM_007_負値と0は範囲外として拒否(inseam_cm):
    assert error_code_of("SELECTED", MACHINE_ID, inseam_cm) == "INSEAM_OUT_OF_RANGE"


def test_UT_HEM_008_存在しない方法を拒否():
    # DBで見つからなかった状態を method=None で表す。
    code = error_code_of("SELECTED", MACHINE_ID, 74, method=None)
    assert code == "INVALID_ALTERATION_METHOD"


def test_UT_HEM_009_Mの範囲で68は拒否():
    code = error_code_of("SELECTED", MACHINE_ID, 68, rule=RULE_M)
    assert code == "INSEAM_OUT_OF_RANGE"


def test_UT_HEM_009_Mの範囲で83は許可():
    assert run("SELECTED", MACHINE_ID, 83, rule=RULE_M).inseam_cm == 83


def test_UT_HEM_009_範囲外メッセージにMの範囲が入る():
    with pytest.raises(AlterationError) as error:
        run("SELECTED", MACHINE_ID, 68, rule=RULE_M)
    assert error.value.message == "股下は70～85cmの整数で指定してください。"


def test_UT_HEM_010_補正対象外の商品は拒否():
    code = error_code_of("SELECTED", MACHINE_ID, 74, rule=RULE_NOT_AVAILABLE)
    assert code == "ALTERATION_NOT_AVAILABLE"
