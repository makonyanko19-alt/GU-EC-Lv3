import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import SelectionForm from "../components/SelectionForm";
import ProductView from "../components/ProductView";
import Checkout from "../components/Checkout";
import OrderResult from "../components/OrderResult";
import CartPage from "../app/cart/page";
import { Totals } from "../components/Common";
import {
  cart,
  method,
  order,
  preview,
  product,
  response,
  skuM,
  skuS,
} from "../lib/test-fixtures";

const mockFetch = jest.fn();
beforeEach(() => {
  global.fetch = mockFetch;
  mockFetch.mockReset();
});
function selectHem(value = "74") {
  fireEvent.change(screen.getByLabelText("裾上げ"), {
    target: { value: "SELECTED" },
  });
  fireEvent.change(screen.getByLabelText("仕上げ方法"), {
    target: { value: method.alterationMethodId },
  });
  if (value)
    fireEvent.change(screen.getByLabelText("股下（cm）"), {
      target: { value },
    });
}
async function toPreview() {
  for (const [label, value] of Object.entries({
    お名前: "テスト 太郎",
    メールアドレス: "test@example.com",
    郵便番号: "1000001",
    都道府県: "東京都",
    市区町村: "千代田区",
    番地: "テスト1-1",
    電話番号: "0312345678",
  })) {
    fireEvent.change(screen.getByLabelText(label), { target: { value } });
  }
  fireEvent.change(screen.getByLabelText("受取方法"), {
    target: { value: "HOME_DELIVERY" },
  });
  fireEvent.change(screen.getByLabelText("支払方法"), {
    target: { value: "WALLET" },
  });
  fireEvent.click(screen.getByRole("button", { name: "最新金額を確認する" }));
  await screen.findByRole("heading", { name: "ご注文内容の確認" });
}
function prepareCheckout(orderResponse: unknown = response(order, 201)) {
  mockFetch
    .mockResolvedValueOnce(response(cart))
    .mockResolvedValueOnce(response(preview))
    .mockImplementationOnce(() => Promise.resolve(orderResponse));
  render(<Checkout cart={cart} />);
}
const submitOrder = () => {
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(
    screen.getByRole("button", { name: "Walletで注文する（模擬決済）" }),
  );
};

test("UT-WEB-001 方法未選択の間は股下を操作できない", () => {
  render(<SelectionForm sku={skuS} methods={[method]} onSubmit={jest.fn()} />);
  fireEvent.change(screen.getByLabelText("裾上げ"), {
    target: { value: "SELECTED" },
  });
  expect(screen.getByLabelText("股下（cm）")).toBeDisabled();
  fireEvent.change(screen.getByLabelText("仕上げ方法"), {
    target: { value: method.alterationMethodId },
  });
  expect(screen.getByLabelText("股下（cm）")).toBeEnabled();
});
test("UT-WEB-002 股下未入力はAPIを呼ばない", async () => {
  mockFetch.mockResolvedValueOnce(response(product));
  render(<ProductView productId={product.productId} />);
  await screen.findByText("動作確認用パンツ");
  selectHem("");
  fireEvent.click(screen.getByRole("button", { name: "カートに追加" }));
  expect(screen.getByRole("alert")).toHaveTextContent("股下を入力");
  expect(
    mockFetch.mock.calls.filter(([, o]) => o.method === "POST"),
  ).toHaveLength(0);
});
test("UT-WEB-003 Sの64cmは拒否し65cmへ修正すると追加できる", async () => {
  const send = jest.fn().mockResolvedValue(undefined);
  render(<SelectionForm sku={skuS} methods={[method]} onSubmit={send} />);
  selectHem("64");
  fireEvent.click(screen.getByRole("button", { name: "カートに追加" }));
  expect(screen.getByRole("alert")).toHaveTextContent("65～80cm");
  expect(send).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("股下（cm）"), {
    target: { value: "65" },
  });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "カートに追加" }));
  await waitFor(() =>
    expect(send).toHaveBeenCalledWith({
      quantity: 1,
      alterationStatus: "SELECTED",
      alterationMethodId: method.alterationMethodId,
      inseamCm: 65,
    }),
  );
});
test.each(["SELECTED", "NONE"])(
  "UT-WEB-004 %s 選択と整合するJSONをカートAPIへ送る",
  async (status) => {
    mockFetch
      .mockResolvedValueOnce(response(product))
      .mockResolvedValueOnce(response(cart));
    render(<ProductView productId={product.productId} />);
    await screen.findByText("動作確認用パンツ");
    if (status === "SELECTED") selectHem();
    fireEvent.click(screen.getByRole("button", { name: "カートに追加" }));
    await screen.findByText("カートに追加しました。");
    const [url, options] = mockFetch.mock.calls[1];
    expect(url).toBe("/api/v1/carts/current/items");
    expect(options.credentials).toBe("same-origin");
    expect(JSON.parse(options.body)).toEqual({
      skuId: skuS.skuId,
      quantity: 1,
      alterationStatus: status,
      alterationMethodId:
        status === "SELECTED" ? method.alterationMethodId : null,
      inseamCm: status === "SELECTED" ? 74 : null,
    });
  },
);
test("UT-WEB-005 D-01の金額を各欄に表示する", () => {
  render(
    <Totals
      money={{
        subtotal: 2014,
        alterationFeeTotal: 0,
        shippingFee: 500,
        totalAmount: 2514,
        taxAmount: 228,
      }}
    />,
  );
  for (const [label, value] of [
    ["商品小計", "￥2,014"],
    ["裾上げ料金", "￥0"],
    ["送料", "￥500"],
    ["合計（税込）", "￥2,514"],
    ["うち消費税", "￥228"],
  ]) {
    expect(screen.getByText(label).parentElement).toHaveTextContent(value);
  }
});
test("UT-WEB-006 PRICE_CHANGEDなら再確認を案内し完了表示しない", async () => {
  prepareCheckout(
    response({ errorCode: "PRICE_CHANGED", message: "価格変更" }, 409),
  );
  await toPreview();
  submitOrder();
  await screen.findByText(/価格が変更されました。最新金額を再確認/);
  expect(
    screen.queryByRole("heading", { name: "ご注文が完了しました" }),
  ).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "最新金額を確認する" }),
  ).toBeEnabled();
});
test("UT-WEB-007 202 UNKNOWNは確認中と表示する", async () => {
  prepareCheckout(
    response(
      {
        ...order,
        orderStatus: "PAYMENT_PENDING",
        paymentStatus: "UNKNOWN",
        nextAction: "WAIT_PAYMENT_RESULT",
      },
      202,
    ),
  );
  await toPreview();
  submitOrder();
  await screen.findByRole("heading", { name: "お支払い結果を確認中です" });
  expect(
    screen.queryByRole("heading", { name: "ご注文が完了しました" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "決済が完了しませんでした" }),
  ).not.toBeInTheDocument();
});
test("UT-WEB-008 送信中の再クリックで注文を重複送信しない", async () => {
  let resolve!: (v: Response) => void;
  const pending = new Promise<Response>((r) => {
    resolve = r;
  });
  prepareCheckout(pending);
  await toPreview();
  submitOrder();
  const button = screen.getByRole("button", { name: "処理中…" });
  expect(button).toBeDisabled();
  fireEvent.click(button);
  expect(
    mockFetch.mock.calls.filter(([url]) => url === "/api/v1/orders"),
  ).toHaveLength(1);
  await act(async () => resolve(response(order, 201)));
  await screen.findByRole("heading", { name: "ご注文が完了しました" });
});
test("UT-WEB-009 確認画面で追加3営業日と返品交換不可を確認できる", async () => {
  prepareCheckout();
  await toPreview();
  expect(
    screen.getByText("通常の配送予定に3営業日追加されます。"),
  ).toBeInTheDocument();
  expect(
    screen.getByText("裾上げした商品の返品・交換はできません。"),
  ).toBeInTheDocument();
});
test("UT-WEB-010 範囲エラー応答後SからMへ変更すると範囲表示を更新する", async () => {
  mockFetch
    .mockResolvedValueOnce(response(product))
    .mockResolvedValueOnce(
      response(
        {
          errorCode: "INSEAM_OUT_OF_RANGE",
          message: "股下は65～80cmで指定してください。",
        },
        422,
      ),
    );
  render(<ProductView productId={product.productId} />);
  await screen.findByText("動作確認用パンツ");
  selectHem("65");
  fireEvent.click(screen.getByRole("button", { name: "カートに追加" }));
  await screen.findByText("股下は65～80cmで指定してください。");
  fireEvent.change(screen.getByLabelText("カラー・サイズ"), {
    target: { value: skuM.skuId },
  });
  expect(
    screen.queryByText("股下は65～80cmで指定してください。"),
  ).not.toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("70～85cm");
  expect(screen.getByText("Mサイズ：70～85cm（1cm刻み）")).toBeInTheDocument();
});
test("補足 決済失敗を注文完了と表示しない", () => {
  render(
    <OrderResult
      order={{
        ...order,
        orderStatus: "PAYMENT_FAILED",
        paymentStatus: "FAILED",
      }}
    />,
  );
  expect(
    screen.getByRole("heading", { name: "決済が完了しませんでした" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "ご注文が完了しました" }),
  ).not.toBeInTheDocument();
});
test("補足 注文通信エラーは自動再送せず手動再送も止める", async () => {
  mockFetch
    .mockResolvedValueOnce(response(cart))
    .mockResolvedValueOnce(response(preview))
    .mockRejectedValueOnce(new TypeError("offline"));
  render(<Checkout cart={cart} />);
  await toPreview();
  submitOrder();
  await screen.findByText(/注文が受け付けられたか確認できません/);
  expect(
    screen.getByRole("button", { name: "Walletで注文する（模擬決済）" }),
  ).toBeDisabled();
  expect(
    mockFetch.mock.calls.filter(([url]) => url === "/api/v1/orders"),
  ).toHaveLength(1);
});
test("補足 受取方法を選ぶ前は支払方法を操作できない", () => {
  render(<Checkout cart={cart} />);
  expect(screen.getByLabelText("支払方法")).toBeDisabled();
});
test("補足 最後の明細を削除すると空カートで購入不可、送料行なし", async () => {
  mockFetch
    .mockResolvedValueOnce(response(cart))
    .mockResolvedValueOnce(response(null, 204))
    .mockResolvedValueOnce(
      response({
        cartId: cart.cartId,
        items: [],
        subtotal: 0,
        alterationFeeTotal: 0,
        shippingFee: 0,
        taxAmount: 0,
        totalAmount: 0,
      }),
    );
  render(<CartPage />);
  await screen.findByText("動作確認用パンツ");
  fireEvent.click(screen.getByRole("button", { name: "削除" }));
  await screen.findByText("カートは空です");
  expect(screen.getByRole("button", { name: "購入手続きへ" })).toBeDisabled();
  expect(screen.queryByText("送料")).not.toBeInTheDocument();
});
test("補足 カートの数量変更でも裾上げの指定を維持する", async () => {
  mockFetch
    .mockResolvedValueOnce(response(cart))
    .mockResolvedValueOnce(response(product))
    .mockResolvedValueOnce(
      response({
        ...cart,
        items: [{ ...cart.items[0], quantity: 2, lineTotal: 2600 }],
        subtotal: 2000,
        alterationFeeTotal: 600,
        totalAmount: 3100,
        taxAmount: 281,
      }),
    );
  render(<CartPage />);
  await screen.findByText("動作確認用パンツ");
  fireEvent.click(screen.getByRole("button", { name: "数量・裾上げを変更" }));
  await screen.findByLabelText("数量");
  fireEvent.change(screen.getByLabelText("数量"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "変更を保存" }));
  await screen.findByText("ブラック / S / 2点");
  const [url, options] = mockFetch.mock.calls[2];
  expect(url).toBe(`/api/v1/carts/current/items/${cart.items[0].cartItemId}`);
  expect(options.method).toBe("PATCH");
  expect(JSON.parse(options.body)).toEqual({
    quantity: 2,
    alterationStatus: "SELECTED",
    alterationMethodId: method.alterationMethodId,
    inseamCm: 74,
  });
});
