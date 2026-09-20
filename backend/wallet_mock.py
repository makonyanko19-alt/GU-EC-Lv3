"""Wallet決済の代役（テスト仕様書 D-08）。

実際の決済事業者へはつながない。結果は環境変数 WALLET_MOCK_RESULT で切り替える。
  SUCCEEDED（既定）… 決済成功
  FAILED        … 事業者が明確な失敗を返す
  TIMEOUT       … 応答なし（結果不明）
カード番号などの支払情報は受け取らず、保存もしない。
"""
import os
import uuid


class WalletTimeout(Exception):
    """決済事業者から応答がない。失敗と断定しない。"""


# 決済要求の記録（テストで「決済要求の回数」を確認するために使う）
requests_log: list[dict] = []


def request_payment(order_number: str, amount: int) -> dict:
    requests_log.append({"orderNumber": order_number, "amount": amount})
    mode = os.environ.get("WALLET_MOCK_RESULT", "SUCCEEDED").upper()
    if mode == "TIMEOUT":
        raise WalletTimeout()
    if mode == "FAILED":
        return {"status": "FAILED", "transactionId": None}
    return {"status": "SUCCEEDED", "transactionId": f"mock-{uuid.uuid4()}"}
