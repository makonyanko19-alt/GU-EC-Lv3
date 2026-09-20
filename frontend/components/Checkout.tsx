"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Address, Cart, CheckoutBody, Order, Preview } from "../lib/types";
import { AlterationNotice, ErrorNotice, ItemDetails, Totals } from "./Common";
import OrderResult from "./OrderResult";
const fields: [keyof Address, string, string][] = [
  ["recipientName", "お名前", "name"],
  ["contactEmail", "メールアドレス", "email"],
  ["postalCode", "郵便番号", "postal-code"],
  ["prefecture", "都道府県", "address-level1"],
  ["city", "市区町村", "address-level2"],
  ["addressLine1", "番地", "address-line1"],
  ["addressLine2", "建物名・部屋番号（任意）", "address-line2"],
  ["phoneNumber", "電話番号", "tel"],
];
const blank: Address = {
  recipientName: "",
  contactEmail: "",
  postalCode: "",
  prefecture: "",
  city: "",
  addressLine1: "",
  addressLine2: "",
  phoneNumber: "",
};
export default function Checkout({
  cart,
  onOrder,
}: {
  cart: Cart;
  onOrder?: (order: Order) => void;
}) {
  const [address, setAddress] = useState<Address>(blank);
  const [reviewCart, setReviewCart] = useState(cart);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [confirmedBody, setConfirmedBody] = useState<CheckoutBody | null>(null);
  const [error, setError] = useState<unknown>(null),
    [busy, setBusy] = useState(false);
  const [accepted, setAccepted] = useState(false),
    [result, setResult] = useState<Order | null>(null);
  const [uncertain, setUncertain] = useState(false);
  const [delivery, setDelivery] = useState(""),
    [payment, setPayment] = useState("");
  const inFlight = useRef(false);
  const altered = reviewCart.items.some(
    (i) => i.alterationStatus === "SELECTED",
  );
  async function confirm(e: React.FormEvent) {
    e.preventDefault();
    if (inFlight.current || !cart.cartId) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    const body: CheckoutBody = {
      cartId: cart.cartId,
      deliveryAddress: { ...address },
      deliveryMethod: "HOME_DELIVERY",
      paymentProvider: "WALLET",
    };
    try {
      const latest = await api<Cart>("/carts/current");
      if (latest.cartId !== cart.cartId || !latest.items.length)
        throw new ApiError(409, {
          message:
            "カートが変更されました。カート画面へ戻って内容を確認してください。",
        });
      const p = await api<Preview>("/checkout/preview", "POST", body);
      setReviewCart(latest);
      setPreview(p);
      setConfirmedBody(body);
      setAccepted(false);
    } catch (e) {
      setError(e);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  async function buy() {
    if (
      inFlight.current ||
      !preview ||
      !confirmedBody ||
      !accepted ||
      uncertain
    )
      return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    // 注文POSTは一度だけ。通信途絶・5xxでは自動再試行しない。
    try {
      const order = await api<Order>("/orders", "POST", {
        ...confirmedBody,
        expectedTotalAmount: preview.totalAmount,
      });
      setResult(order);
      onOrder?.(order);
    } catch (e) {
      setError(e);
      if (e instanceof ApiError && e.status >= 400 && e.status < 500) {
        setPreview(null);
        setConfirmedBody(null);
        setAccepted(false);
        if (e.body.errorCode === "PRICE_CHANGED")
          setError(
            new ApiError(409, {
              ...e.body,
              message:
                "価格が変更されました。最新金額を再確認してください。注文は確定していません。",
            }),
          );
      } else setUncertain(true);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }
  if (result) return <OrderResult order={result} />;
  if (!cart.items.length || !cart.cartId)
    return (
      <>
        <h1>購入手続き</h1>
        <p>カートに商品がありません。</p>
        <Link href="/">商品を見る</Link>
      </>
    );
  return (
    <>
      <p className="eyebrow">CHECKOUT / {preview ? "最終確認" : "お届け先"}</p>
      <h1>{preview ? "ご注文内容の確認" : "購入手続き"}</h1>
      <ErrorNotice error={error} />
      {uncertain && (
        <div role="alert" className="notice">
          注文が受け付けられたか確認できません。再送や新しい注文をせず、注文記録の確認が必要です。
        </div>
      )}
      <div className="two-column">
        <section>
          {!preview ? (
            <form onSubmit={confirm}>
              <fieldset disabled={busy || uncertain} className="card">
                <legend>お届け先</legend>
                <p className="muted">
                  動作確認には架空の氏名・住所を入力してください。
                </p>
                {fields.map(([name, label, complete]) => (
                  <label key={name}>
                    {label}
                    <input
                      name={name}
                      aria-label={label}
                      autoComplete={complete}
                      required={name !== "addressLine2"}
                      type={
                        name === "contactEmail"
                          ? "email"
                          : name === "phoneNumber"
                            ? "tel"
                            : "text"
                      }
                      maxLength={name === "contactEmail" ? 254 : 200}
                      value={address[name]}
                      onChange={(e) =>
                        setAddress({ ...address, [name]: e.target.value })
                      }
                    />
                  </label>
                ))}
                <label>
                  受取方法
                  <select
                    aria-label="受取方法"
                    required
                    value={delivery}
                    onChange={(e) => {
                      setDelivery(e.target.value);
                      setPayment("");
                    }}
                  >
                    <option value="">選択してください</option>
                    <option value="HOME_DELIVERY">自宅配送</option>
                  </select>
                </label>
                <label>
                  支払方法
                  <select
                    aria-label="支払方法"
                    required
                    disabled={!delivery}
                    value={payment}
                    onChange={(e) => setPayment(e.target.value)}
                  >
                    <option value="">受取方法を選んでから選択</option>
                    <option value="WALLET">Wallet（模擬決済）</option>
                  </select>
                </label>
                <p>
                  模擬決済のため、カード番号の入力や実際の課金はありません。
                </p>
                <button
                  type="submit"
                  disabled={busy || uncertain || !delivery || !payment}
                >
                  {busy ? "確認中…" : "最新金額を確認する"}
                </button>
              </fieldset>
            </form>
          ) : (
            <>
              <div className="card">
                <h2>お届け先</h2>
                <p>{address.recipientName} 様</p>
                <p>
                  〒{address.postalCode} {address.prefecture}
                  {address.city}
                  {address.addressLine1} {address.addressLine2}
                </p>
                <p>
                  {address.contactEmail} / {address.phoneNumber}
                </p>
                <p>受取：自宅配送 / 支払：Wallet（模擬決済）</p>
                <p>配送予定日：{preview.estimatedDeliveryDate}</p>
              </div>
              {altered && (
                <AlterationNotice
                  days={Math.max(
                    ...reviewCart.items.map((i) => i.additionalBusinessDays),
                  )}
                />
              )}
              {preview.stockShortages.length > 0 && (
                <div role="alert" className="notice error">
                  <p>在庫が不足しています。カートで数量を変更してください。</p>
                  {preview.stockShortages.map((s) => (
                    <p key={s.skuId}>
                      {
                        reviewCart.items.find((i) => i.skuId === s.skuId)
                          ?.productName
                      }
                      ：必要 {s.requestedQuantity}点 / 在庫{" "}
                      {s.availableQuantity}点
                    </p>
                  ))}
                  <Link href="/cart">カートへ戻る</Link>
                </div>
              )}
              <div className="card">
                <label className="check">
                  <input
                    type="checkbox"
                    checked={accepted}
                    disabled={busy || uncertain}
                    onChange={(e) => setAccepted(e.target.checked)}
                  />
                  注文内容・最新金額
                  {altered ? "・追加日数・裾上げ商品の返品交換不可" : ""}
                  を確認しました
                </label>
                <button
                  onClick={buy}
                  disabled={
                    busy ||
                    !accepted ||
                    uncertain ||
                    !!preview.stockShortages.length
                  }
                >
                  {busy ? "処理中…" : "Walletで注文する（模擬決済）"}
                </button>
                <button
                  className="text-button"
                  disabled={busy || uncertain}
                  onClick={() => {
                    setPreview(null);
                    setConfirmedBody(null);
                    setAccepted(false);
                  }}
                >
                  入力内容に戻る
                </button>
              </div>
            </>
          )}
          {reviewCart.items.map((item) => (
            <article className="card" key={item.cartItemId}>
              <ItemDetails item={item} />
            </article>
          ))}
        </section>
        <aside className="card summary">
          <h2>{preview ? "最新のお支払い金額" : "カートの金額"}</h2>
          <Totals money={preview || cart} />
        </aside>
      </div>
    </>
  );
}
