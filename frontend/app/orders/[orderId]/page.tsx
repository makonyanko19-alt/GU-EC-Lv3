"use client";
import { use, useCallback, useEffect, useState } from "react";
import { api } from "../../../lib/api";
import type { Order } from "../../../lib/types";
import OrderResult from "../../../components/OrderResult";
import { ErrorNotice } from "../../../components/Common";
export default function OrderPage({
  params,
}: {
  params: Promise<{ orderId: string }>;
}) {
  const { orderId } = use(params);
  const [order, setOrder] = useState<Order | null>(null),
    [error, setError] = useState<unknown>(null),
    [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      setOrder(await api<Order>(`/orders/${encodeURIComponent(orderId)}`));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [orderId]);
  useEffect(() => {
    void refresh();
  }, [refresh]);
  return (
    <>
      <ErrorNotice error={error} />
      {order ? (
        <OrderResult order={order} />
      ) : (
        <h1>{busy ? "注文を確認しています…" : "注文を取得できませんでした"}</h1>
      )}
      <button className="secondary" disabled={busy} onClick={refresh}>
        {busy ? "確認中…" : "注文状況を再取得する"}
      </button>
      {order?.paymentStatus === "UNKNOWN" && (
        <p className="muted">
          現在の模擬決済では、確認中の結果を自動確定する機能は未実装です。再取得しても状態が変わらない場合があります。
        </p>
      )}
      <p className="muted">同じブラウザで作成した直近の注文を照会できます。</p>
    </>
  );
}
