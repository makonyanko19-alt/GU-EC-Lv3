export type ApiErrorBody = {
  errorCode?: string;
  message?: string;
  fieldErrors?: { field: string; message: string }[];
  traceId?: string;
};
export class ApiError extends Error {
  constructor(
    public status: number,
    public body: ApiErrorBody,
  ) {
    super(body.message || `通信エラー（${status}）`);
  }
}
// Cookieはブラウザが管理。注文POSTの自動再送はしない。
export async function api<T>(
  path: string,
  method = "GET",
  data?: unknown,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      credentials: "same-origin",
      cache: "no-store",
      headers:
        data === undefined ? undefined : { "Content-Type": "application/json" },
      body: data === undefined ? undefined : JSON.stringify(data),
    });
  } catch {
    throw new ApiError(0, {
      errorCode: "NETWORK_ERROR",
      message: "通信が途切れました。接続状況を確認してください。",
    });
  }
  if (response.status === 204) return undefined as T;
  let body;
  try {
    body = await response.json();
  } catch {
    throw new ApiError(response.status, {
      message: "サーバーの応答を読み取れませんでした。",
    });
  }
  if (!response.ok) throw new ApiError(response.status, body);
  return body as T;
}
export function errorMessage(error: unknown): string {
  return error instanceof Error
    ? error.message
    : "処理を完了できませんでした。";
}
export const sampleProductId = "11111111-1111-4111-8111-111111111111";
export const yen = (n: number) =>
  new Intl.NumberFormat("ja-JP", { style: "currency", currency: "JPY" }).format(
    n,
  );
