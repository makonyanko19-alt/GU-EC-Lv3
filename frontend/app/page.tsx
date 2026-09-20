import ProductView from "../components/ProductView";
import { sampleProductId } from "../lib/api";
export default function Home() {
  return <ProductView productId={sampleProductId} />;
}
