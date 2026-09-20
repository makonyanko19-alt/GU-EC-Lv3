import Link from "next/link";
import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "GU EC | 開発演習",
  description: "裾上げ指定から購入までの開発演習",
  robots: { index: false, follow: false },
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ja">
      <body>
        <a className="skip" href="#main">
          本文へ
        </a>
        <div className="demo-banner">
          開発演習用サイト · 決済はシミュレーションです
        </div>
        <header>
          <Link href="/" className="brand" aria-label="GU EC トップ">
            GU<span>EC STUDY</span>
          </Link>
          <nav aria-label="メイン">
            <Link href="/">商品を見る</Link>
            <Link href="/cart">カート</Link>
          </nav>
        </header>
        <main id="main">{children}</main>
        <footer>
          Tech0 個人課題 / GU EC Lv3
          <br />
          <small>
            学習用の非公式サイトです。実際の商品購入・課金は行いません。
          </small>
        </footer>
      </body>
    </html>
  );
}
