"""裾上げ指定の判定ルール（DBを使わない部分）。

DBに接続しないので、CI（MySQLも.envもない環境）で単体テストできる。
DBから条件を取得して判定を完成させる処理は alteration.py にある。

エラーコードの決め方
- テスト仕様書のケースに明記されたコードはそれに従う
- 明記がなく、設計仕様書17章に個別のコードがあればそれに従う
- どちらにもないものは、テスト仕様書17章の実装照合事項として今回定める
HTTPステータスは、入力不備を422とするテスト仕様書の方針（DEC-08）に合わせる。
"""
from dataclasses import dataclass
from uuid import UUID

ALTERATION_NONE = "NONE"
ALTERATION_SELECTED = "SELECTED"


class AlterationError(Exception):
    """裾上げ指定を受け付けられないときに発生させる例外。

    呼び出し元（APIの関数）で受け取り、error_responseでJSONへ変換する。
    """

    def __init__(
        self,
        status_code: int,
        error_code: str,
        message: str,
        field: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        self.field = field


@dataclass(frozen=True)
class AlterationSelection:
    """検証を通過した裾上げ指定。カート保存などでそのまま使う。"""

    alteration_status: str
    alteration_method_id: str | None
    inseam_cm: int | None
    alteration_fee: int
    additional_business_days: int


NO_ALTERATION = AlterationSelection(ALTERATION_NONE, None, None, 0, 0)


def normalize_uuid(value: object, field: str) -> str:
    """ハイフン付きUUIDか確認し、小文字の表記にそろえて返す。"""
    try:
        normalized = str(UUID(value))
        if normalized != value.lower():
            raise ValueError("Invalid UUID format")
    except (ValueError, TypeError, AttributeError):
        raise AlterationError(
            422,
            "INVALID_ID_FORMAT",
            "IDはハイフン付きのUUID形式で指定してください。",
            field,
        )
    return normalized


def check_alteration_input(
    alteration_status: object,
    alteration_method_id: object,
    inseam_cm: object,
) -> str | None:
    """DBを見る前に判定できる部分を確認する。

    問題がなければ、小文字にそろえた仕上げ方法ID（裾上げなしはNone）を返す。
    """
    # 1. 裾上げ有無の値そのもの（設計17章 INVALID_ALTERATION_STATUS）
    if alteration_status not in (ALTERATION_NONE, ALTERATION_SELECTED):
        raise AlterationError(
            422,
            "INVALID_ALTERATION_STATUS",
            "裾上げの有無はNONEまたはSELECTEDで指定してください。",
            "alterationStatus",
        )

    # 2. 裾上げなしに方法・股下が付いている（UT-HEM-003 前者）
    if alteration_status == ALTERATION_NONE:
        if alteration_method_id is not None or inseam_cm is not None:
            raise AlterationError(
                422,
                "INVALID_ALTERATION_COMBINATION",
                "裾上げなしの場合、仕上げ方法と股下は指定できません。",
                "alterationStatus",
            )
        return None

    # 3. 裾上げありなのに方法・股下が足りない（UT-HEM-003 後二者）
    if alteration_method_id is None:
        raise AlterationError(
            422,
            "ALTERATION_INPUT_REQUIRED",
            "仕上げ方法を選択してください。",
            "alterationMethodId",
        )
    if inseam_cm is None:
        raise AlterationError(
            422,
            "ALTERATION_INPUT_REQUIRED",
            "股下を入力してください。",
            "inseamCm",
        )

    # 4. 股下が整数でない（UT-HEM-006）。True/Falseもintの仲間なので除外する。
    if isinstance(inseam_cm, bool) or not isinstance(inseam_cm, int):
        raise AlterationError(
            422,
            "INVALID_INPUT_TYPE",
            "股下は整数で指定してください。",
            "inseamCm",
        )

    return normalize_uuid(alteration_method_id, "alterationMethodId")


def check_alteration_rule(
    alteration_method_id: str,
    inseam_cm: int,
    rule: dict | None,
    method: dict | None,
) -> AlterationSelection:
    """DBから取得した条件と、裾上げありの指定を照らし合わせる。

    rule: 商品×サイズの裾上げ条件（行がなければNone）
    method: 有効な仕上げ方法（存在しない・無効ならNone）
    """
    # 5. 商品・サイズが裾上げ対象外（UT-HEM-010）
    # ルール行がない場合は、商品詳細APIと同じく対象外として扱う。
    if rule is None or not rule["is_alteration_available"]:
        raise AlterationError(
            422,
            "ALTERATION_NOT_AVAILABLE",
            "この商品・サイズは裾上げを承っていません。",
            "alterationStatus",
        )

    # 6. 仕上げ方法が存在しない・無効（UT-HEM-008）
    if method is None:
        raise AlterationError(
            422,
            "INVALID_ALTERATION_METHOD",
            "選択された仕上げ方法は利用できません。",
            "alterationMethodId",
        )

    # 7. 範囲と刻み幅（UT-HEM-004／005／007／009）
    # 設計17章では刻み幅違反も INSEAM_OUT_OF_RANGE にまとめている。
    min_cm = rule["min_inseam_cm"]
    max_cm = rule["max_inseam_cm"]
    step_cm = rule["inseam_step_cm"]
    if (
        inseam_cm < min_cm
        or inseam_cm > max_cm
        or (inseam_cm - min_cm) % step_cm != 0
    ):
        raise AlterationError(
            422,
            "INSEAM_OUT_OF_RANGE",
            f"股下は{min_cm}～{max_cm}cmの整数で指定してください。",
            "inseamCm",
        )

    return AlterationSelection(
        alteration_status=ALTERATION_SELECTED,
        alteration_method_id=alteration_method_id,
        inseam_cm=inseam_cm,
        alteration_fee=int(method["alteration_fee"]),
        additional_business_days=int(method["additional_business_days"]),
    )
