"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { Cart, CartItem, Product } from "../../lib/types";
import { ErrorNotice, ItemDetails, Totals } from "../../components/Common";
import SelectionForm from "../../components/SelectionForm";
export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null),
    [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<{
    item: CartItem;
    product: Product;
  } | null>(null);
  const reload = () => api<Cart>("/carts/current").then(setCart);
  useEffect(() => {
    reload().catch(setError);
  }, []);
  return (
    <>
      <p className="eyebrow">SHOPPING BAG</p>
      <h1>カート</h1>
      <ErrorNotice error={error} />
      {!cart && !error && <p role="status">カートを読み込んでいます…</p>}
      {cart && (
        <div className="two-column">
          <section>
            {cart.items.length === 0 ? (
              <div className="card">
                <h2>カートは空です</h2>
                <Link href="/">商品を見る →</Link>
              </div>
            ) : (
              cart.items.map((item) => (
                <article key={item.cartItemId} className="card">
                  <ItemDetails item={item} />
                  {item.quantity > item.availableQuantity && (
                    <p role="alert" className="field-error">
                      在庫が不足しています。現在 {item.availableQuantity}
                      点です。
                    </p>
                  )}
                  <div className="actions">
                    <button
                      className="secondary"
                      disabled={busy || !!editing}
                      onClick={async () => {
                        setBusy(true);
                        setError(null);
                        try {
                          const product = await api<Product>(
                            `/products/${item.productId}`,
                          );
                          setEditing({ item, product });
                        } catch (e) {
                          setError(e);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      数量・裾上げを変更
                    </button>
                    <button
                      className="text-button"
                      disabled={busy || !!editing}
                      onClick={async () => {
                        setBusy(true);
                        setError(null);
                        try {
                          await api(
                            `/carts/current/items/${item.cartItemId}`,
                            "DELETE",
                          );
                          await reload();
                        } catch (e) {
                          setError(e);
                        } finally {
                          setBusy(false);
                        }
                      }}
                    >
                      削除
                    </button>
                  </div>
                  {editing?.item.cartItemId === item.cartItemId &&
                    (() => {
                      const sku = editing.product.skus.find(
                        (s) => s.skuId === item.skuId,
                      );
                      return sku ? (
                        <div className="edit-panel">
                          <SelectionForm
                            key={item.cartItemId}
                            sku={sku}
                            methods={editing.product.alterationMethods}
                            initial={{
                              quantity: item.quantity,
                              alterationStatus:
                                item.alterationStatus === "SELECTED"
                                  ? "SELECTED"
                                  : "NONE",
                              alterationMethodId: item.alterationMethodId,
                              inseamCm: item.inseamCm,
                            }}
                            label="変更を保存"
                            onSubmit={async (value) => {
                              setError(null);
                              setBusy(true);
                              try {
                                setCart(
                                  await api<Cart>(
                                    `/carts/current/items/${item.cartItemId}`,
                                    "PATCH",
                                    value,
                                  ),
                                );
                                setEditing(null);
                              } catch (e) {
                                setError(e);
                              } finally {
                                setBusy(false);
                              }
                            }}
                          />
                          <button
                            className="text-button"
                            disabled={busy}
                            onClick={() => setEditing(null)}
                          >
                            キャンセル
                          </button>
                        </div>
                      ) : (
                        <p>この商品の販売情報を取得できません。</p>
                      );
                    })()}
                </article>
              ))
            )}
          </section>
          <aside className="card summary">
            <h2>お支払い金額</h2>
            <Totals money={cart} empty={!cart.items.length} />
            {cart.items.length > 0 && !editing && !busy ? (
              <Link className="button" href="/checkout">
                購入手続きへ
              </Link>
            ) : (
              <button disabled>購入手続きへ</button>
            )}
            <p className="muted">金額と在庫は注文前にもう一度確認します。</p>
          </aside>
        </div>
      )}
    </>
  );
}
