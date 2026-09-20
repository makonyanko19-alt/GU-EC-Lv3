"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { api, yen } from "../lib/api";
import type { Product } from "../lib/types";
import SelectionForm from "./SelectionForm";
import { ErrorNotice } from "./Common";
export default function ProductView({ productId }: { productId: string }) {
  const [product, setProduct] = useState<Product | null>(null);
  const [skuId, setSkuId] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [added, setAdded] = useState(false);
  const [saving, setSaving] = useState(false);
  useEffect(() => {
    let active = true;
    api<Product>(`/products/${encodeURIComponent(productId)}`)
      .then((p) => {
        if (active) {
          setProduct(p);
          setSkuId(p.skus[0]?.skuId || "");
        }
      })
      .catch((e) => {
        if (active) setError(e);
      });
    return () => {
      active = false;
    };
  }, [productId]);
  const sku = product?.skus.find((s) => s.skuId === skuId);
  if (!product)
    return (
      <>
        <h1>商品詳細</h1>
        <ErrorNotice error={error} />
        {!error && <p role="status">商品を読み込んでいます…</p>}
      </>
    );
  return (
    <>
      <p className="eyebrow">PRODUCT / 商品詳細</p>
      <div className="product-grid">
        <div className="product-visual" aria-label="商品写真は未登録">
          <span>PANTS</span>
          <div className="pants" aria-hidden="true" />
          <small>商品イメージ（写真未登録）</small>
        </div>
        <section>
          <p className="muted">{product.productCode}</p>
          <h1>{product.productName}</h1>
          <p>{product.description}</p>
          {sku && (
            <p className="price">
              {yen(sku.sellingPrice)}
              <small>税込</small>
            </p>
          )}
          <label>
            カラー・サイズ
            <select
              aria-label="カラー・サイズ"
              disabled={saving}
              value={skuId}
              onChange={(e) => {
                setSkuId(e.target.value);
                setError(null);
                setAdded(false);
              }}
            >
              {product.skus.map((s) => (
                <option key={s.skuId} value={s.skuId}>
                  {s.colorName} / {s.sizeCode}
                  {!s.isAvailable ? "（在庫なし）" : ""}
                </option>
              ))}
            </select>
          </label>
          {sku && (
            <>
              <p className="stock">
                {sku.isAvailable
                  ? `在庫 ${sku.availableQuantity}点`
                  : "在庫がありません"}
              </p>
              <SelectionForm
                sku={sku}
                methods={product.alterationMethods}
                onSubmit={async (selection) => {
                  setError(null);
                  setAdded(false);
                  setSaving(true);
                  try {
                    await api("/carts/current/items", "POST", {
                      skuId,
                      ...selection,
                    });
                    setAdded(true);
                  } catch (e) {
                    setError(e);
                  } finally {
                    setSaving(false);
                  }
                }}
              />
            </>
          )}
          <ErrorNotice error={error} />
          {added && (
            <div role="status" className="notice success">
              カートに追加しました。<Link href="/cart">カートを確認する →</Link>
            </div>
          )}
        </section>
      </div>
    </>
  );
}
