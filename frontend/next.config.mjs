// ブラウザは同じホストの /api を呼び、Next.js が FastAPI に中継する。
export default {
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/v1/:path*`,
      },
    ];
  },
};
