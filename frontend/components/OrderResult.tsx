import type { Order } from "../lib/types";
import { ItemDetails, Totals } from "./Common";
export default function OrderResult({ order }: { order: Order }) {
  const confirmed =
    order.orderStatus === "CONFIRMED" && order.paymentStatus === "SUCCEEDED";
  const failed =
    order.orderStatus === "PAYMENT_FAILED" && order.paymentStatus === "FAILED";
  return (
    <>
      <h1>
        {confirmed
          ? "ご注文が完了しました"
          : failed
            ? "決済が完了しませんでした"
            : "お支払い結果を確認中です"}
      </h1>
      <div role="status" className={`notice ${confirmed ? "success" : ""}`}>
        {confirmed
          ? "注文内容を受け付けました。"
          : failed
            ? "お支払いは失敗しました。注文は確定していません。この演習では決済の再試行はまだ利用できません。"
            : "成功・失敗はまだ確定していません。重複購入を避けるため、新しい注文をせずに結果を確認してください。"}
      </div>
      <p>
        注文番号：<strong>{order.orderNumber}</strong>
      </p>
      <p>
        {confirmed ? "配送予定日" : "確定した場合の配送予定日"}：
        {order.estimatedDeliveryDate}
      </p>
      <div className="two-column">
        <section>
          {order.items.map((item, i) => (
            <article className="card" key={i}>
              <ItemDetails item={item} />
            </article>
          ))}
        </section>
        <aside className="card summary">
          <h2>注文金額</h2>
          <Totals money={order} />
        </aside>
      </div>
    </>
  );
}
