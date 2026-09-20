import { ApiError, errorMessage, yen } from "../lib/api";
import type { Line, Money } from "../lib/types";
export function ErrorNotice({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <div role="alert" className="notice error">
      <p>{errorMessage(error)}</p>
      {error instanceof ApiError &&
        error.body.fieldErrors?.map((e, i) => <p key={i}>{e.message}</p>)}
      {error instanceof ApiError && error.body.traceId && (
        <small>お問い合わせ用ID：{error.body.traceId}</small>
      )}
    </div>
  );
}
export function Totals({
  money,
  empty = false,
}: {
  money: Money;
  empty?: boolean;
}) {
  return (
    <dl className="totals">
      <div>
        <dt>商品小計</dt>
        <dd>{yen(money.subtotal)}</dd>
      </div>
      {!empty && (
        <>
          <div>
            <dt>裾上げ料金</dt>
            <dd>{yen(money.alterationFeeTotal)}</dd>
          </div>
          <div>
            <dt>送料</dt>
            <dd>{yen(money.shippingFee)}</dd>
          </div>
        </>
      )}
      <div className="total">
        <dt>合計（税込）</dt>
        <dd>{yen(money.totalAmount)}</dd>
      </div>
      <div>
        <dt>うち消費税</dt>
        <dd>{yen(money.taxAmount)}</dd>
      </div>
    </dl>
  );
}
export function ItemDetails({ item }: { item: Line }) {
  return (
    <>
      <h3>{item.productName}</h3>
      <p>
        {item.colorName} / {item.sizeCode} / {item.quantity}点
      </p>
      <p>商品単価 {yen(item.unitPrice)}</p>
      <p>
        {item.alterationStatus === "SELECTED"
          ? `${item.alterationMethodName}・股下 ${item.inseamCm}cm（裾上げ ${yen(item.alterationFee)} / 点）`
          : "裾上げなし"}
      </p>
      <strong>明細合計 {yen(item.lineTotal)}</strong>
    </>
  );
}
export function AlterationNotice({ days = 3 }: { days?: number }) {
  return (
    <div className="notice">
      <strong>裾上げをご指定のお客様へ</strong>
      <p>通常の配送予定に{days}営業日追加されます。</p>
      <p>裾上げした商品の返品・交換はできません。</p>
    </div>
  );
}
