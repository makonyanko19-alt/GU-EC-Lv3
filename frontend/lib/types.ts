export type Method = {
  alterationMethodId: string;
  methodName: string;
  alterationFee: number;
  additionalBusinessDays: number;
};
export type Sku = {
  skuId: string;
  colorName: string;
  sizeCode: string;
  sellingPrice: number;
  availableQuantity: number;
  isAvailable: boolean;
  isAlterationAvailable: boolean;
  minInseamCm: number | null;
  maxInseamCm: number | null;
  inseamStepCm: number | null;
};
export type Product = {
  productId: string;
  productName: string;
  productCode: string;
  description: string | null;
  skus: Sku[];
  alterationMethods: Method[];
};
export type Selection = {
  quantity: number;
  alterationStatus: "NONE" | "SELECTED";
  alterationMethodId: string | null;
  inseamCm: number | null;
};
export type Line = {
  productName: string;
  skuId: string;
  colorName: string;
  sizeCode: string;
  unitPrice: number;
  quantity: number;
  alterationStatus: string;
  alterationMethodName: string | null;
  alterationFee: number;
  inseamCm: number | null;
  lineTotal: number;
};
export type CartItem = Line & {
  cartItemId: string;
  productId: string;
  alterationMethodId: string | null;
  additionalBusinessDays: number;
  availableQuantity: number;
};
export type Money = {
  subtotal: number;
  alterationFeeTotal: number;
  shippingFee: number;
  taxAmount: number;
  totalAmount: number;
};
export type Cart = Money & { cartId: string | null; items: CartItem[] };
export type Address = {
  recipientName: string;
  contactEmail: string;
  postalCode: string;
  prefecture: string;
  city: string;
  addressLine1: string;
  addressLine2: string;
  phoneNumber: string;
};
export type CheckoutBody = {
  cartId: string;
  deliveryAddress: Address;
  deliveryMethod: "HOME_DELIVERY";
  paymentProvider: "WALLET";
};
export type Preview = Money & {
  estimatedDeliveryDate: string;
  stockShortages: {
    skuId: string;
    requestedQuantity: number;
    availableQuantity: number;
  }[];
};
export type Order = Money & {
  orderId: string;
  orderNumber: string;
  orderStatus: string;
  paymentStatus: string;
  nextAction: string;
  estimatedDeliveryDate: string;
  items: Line[];
};
