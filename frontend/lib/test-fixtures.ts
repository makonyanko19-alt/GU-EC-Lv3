import type { Cart, Order, Product, Sku } from "../lib/types";
export const skuS: Sku = {
  skuId: "22222222-2222-4222-8222-222222222221",
  colorName: "ブラック",
  sizeCode: "S",
  sellingPrice: 1000,
  availableQuantity: 10,
  isAvailable: true,
  isAlterationAvailable: true,
  minInseamCm: 65,
  maxInseamCm: 80,
  inseamStepCm: 1,
};
export const skuM: Sku = {
  ...skuS,
  skuId: "22222222-2222-4222-8222-222222222222",
  sizeCode: "M",
  minInseamCm: 70,
  maxInseamCm: 85,
};
export const method = {
  alterationMethodId: "33333333-3333-4333-8333-333333333333",
  methodName: "ミシン仕上げ",
  alterationFee: 300,
  additionalBusinessDays: 3,
};
export const product: Product = {
  productId: "11111111-1111-4111-8111-111111111111",
  productCode: "TEST-PANTS-001",
  productName: "動作確認用パンツ",
  description: "確認用",
  skus: [skuS, skuM],
  alterationMethods: [method],
};
export const cart: Cart = {
  cartId: "44444444-4444-4444-8444-444444444444",
  items: [
    {
      cartItemId: "55555555-5555-4555-8555-555555555555",
      productId: product.productId,
      productName: product.productName,
      skuId: skuS.skuId,
      colorName: "ブラック",
      sizeCode: "S",
      unitPrice: 1000,
      quantity: 1,
      alterationStatus: "SELECTED",
      alterationMethodId: method.alterationMethodId,
      alterationMethodName: method.methodName,
      alterationFee: 300,
      additionalBusinessDays: 3,
      inseamCm: 74,
      availableQuantity: 10,
      lineTotal: 1300,
    },
  ],
  subtotal: 1000,
  alterationFeeTotal: 300,
  shippingFee: 500,
  taxAmount: 163,
  totalAmount: 1800,
};
export const preview = {
  subtotal: 1000,
  alterationFeeTotal: 300,
  shippingFee: 500,
  taxAmount: 163,
  totalAmount: 1800,
  estimatedDeliveryDate: "2026-09-28",
  stockShortages: [],
};
export const order: Order = {
  ...preview,
  orderId: "66666666-6666-4666-8666-666666666666",
  orderNumber: "TEST-ORDER-001",
  orderStatus: "CONFIRMED",
  paymentStatus: "SUCCEEDED",
  nextAction: "NONE",
  items: cart.items,
};
export const response = (body: unknown, status = 200) =>
  ({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }) as Response;
