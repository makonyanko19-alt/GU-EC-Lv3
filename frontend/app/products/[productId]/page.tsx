import ProductView from "../../../components/ProductView";
export default async function Page({
  params,
}: {
  params: Promise<{ productId: string }>;
}) {
  const { productId } = await params;
  return <ProductView productId={productId} />;
}
