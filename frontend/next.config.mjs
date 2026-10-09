// ブラウザは同じホストの /api を呼び、Next.js が FastAPI に中継する。
// 中継先 BACKEND_URL は「ビルド時」の値が使われる（Azure上で後から変えても反映されない）。
export default {
  poweredByHeader: false,
  // Azureへ載せるとき、動かすのに必要なファイルだけを .next/standalone にまとめる。
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/v1/:path*`,
      },
    ];
  },
};