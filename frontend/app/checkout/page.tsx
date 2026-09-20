"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Checkout from "../../components/Checkout";
import { ErrorNotice } from "../../components/Common";
import { api } from "../../lib/api";
import type { Cart } from "../../lib/types";
export default function CheckoutPage() {
  const [cart, setCart] = useState<Cart | null>(null),
    [error, setError] = useState<unknown>(null);
  const router = useRouter();
  useEffect(() => {
    api<Cart>("/carts/current").then(setCart).catch(setError);
  }, []);
  return cart ? (
    <Checkout
      cart={cart}
      onOrder={(order) => router.replace(`/orders/${order.orderId}`)}
    />
  ) : (
    <>
      <h1>購入手続き</h1>
      <ErrorNotice error={error} />
      {!error && <p role="status">読み込んでいます…</p>}
    </>
  );
}
