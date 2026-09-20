"""業務ルールで入力や操作を受け付けないときの共通例外。

呼び出し元（APIの関数）で受け取り、error_responseでJSONへ変換する。
裾上げ指定の AlterationError と同じ形（ステータス・errorCode・message・field）。
"""


class BusinessRuleError(Exception):
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
