# Package 3：購入画面（Next.js）

PR #4 マージ後の `main`（`4a9007c`）の FastAPI に合わせた追加パッケージです。
商品詳細 → 裾上げ指定 → カート → 配送先入力・購入確認 → 模擬Wallet決済 → 注文結果をブラウザで操作します。

## 必要な環境と起動

- Node.js 22以上（このパッケージの検証とCIはNode.js 24）。`node -v` と `npm -v` で確認。
- Package 2までのBackend、SQL 001〜005、確認用データ003が準備済み。
- Docker Desktopが起動済み。DBの接続先は引き続きrepo直下の `.env`。
- フロントエンドにDBのパスワードは書きません。

PowerShellを2つ使用します。起動するコマンドは実行したままにします。

### ターミナル1：repo直下でDBとAPIを起動

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir backend --reload --reload-dir backend
```

### ターミナル2：repo直下から画面を起動

```powershell
cd frontend
npm ci
npm test
npm run build
npm run dev
```

ブラウザで **http://127.0.0.1:3000** を開きます。途中で `localhost` へ切り替えるとCookieが別扱いになるので、127.0.0.1に統一してください。
`npm ci` はpackage-lock.jsonの版をインストールするコマンドです。通常は初回か依存ファイルの変更時のみ実行します。
`npm test` はJest、`npm run build` は配布用ビルドの確認、`npm run dev` は開発サーバーの起動です。

標準設定では `.env.local` の作成は不要です。APIの起動先を変更する場合のみ `frontend/.env.example` を `.env.local` にコピーし、`BACKEND_URL`を調整してNext.jsを再起動します。
PowerShellでnpm.ps1の実行ポリシーに関するエラーが出た場合は、上記コマンドの `npm` を `npm.cmd` に替えて実行できます。

## 動作確認の順序（本人PCで実施する）

1. トップ画面に動作確認用パンツが表示される。
2. Sサイズ・裾上げあり・ミシン仕上げを選ぶ。方法未選択の間は股下を操作できない。
3. 64cmを入力して追加すると「65～80cm」のエラー。74cmへ変更して追加する。
4. カートに「ミシン仕上げ・股下74cm」が表示される。1点なら商品1,000円＋補正300円＋送料500円＝合計1,800円、内税163円。
5. 「数量・裾上げを変更」で2点へ変更できる。1点に戻して購入手続きへ進む。
6. 架空の配送先を入力し、受取方法「自宅配送」、支払方法「Wallet（模擬決済）」を選ぶ。
7. 「最新金額を確認する」で最新金額・配送予定日・追加3営業日・返品交換不可を確認する。
8. 確認チェックを付け、「Walletで注文する（模擬決済）」を押す。
9. 成功時に注文番号と「ご注文が完了しました」が表示される。再読み込みでも同じ注文が照会できる。

確認用データの価格・補正料を変更している場合、上記の金額と異なります。現時点のDB値が表示されます。

## 仕組みとコードの役割

| ファイル | 役割 |
|---|---|
| `app/page.tsx` | 確認用商品の入口 |
| `components/ProductView.tsx` | P-01から商品・SKU・裾上げ条件を取得 |
| `components/SelectionForm.tsx` | 数量・裾上げ有無・方法・股下を検証。カート編集でも共用 |
| `app/cart/page.tsx` | C-01〜04による取得・追加後の確認・変更・削除 |
| `components/Checkout.tsx` | 配送先入力、CK-01で金額を取得、確認後O-01へ送信 |
| `components/OrderResult.tsx` | 注文状態と決済状態で成功・失敗・確認中を区別 |
| `app/orders/[orderId]/page.tsx` | O-02で注文を再取得 |
| `lib/api.ts` | JSON通信、Cookie引継ぎ、共通エラー処理 |
| `next.config.mjs` | `/api/v1`をFastAPIへ中継。ブラウザからは同じホストへアクセス |
| `__tests__/purchase.test.tsx` | UT-WEB-001〜010と補足テスト |

CookieはHttpOnlyのままブラウザが管理し、JavaScriptでトークンを読み取りません。
金額の確定値はAPIの応答を表示します。商品画面だけは選択時の概算を表示し、注文時はCK-01の金額を`expectedTotalAmount`として送り、Backendが再計算します。
`useState`は入力や表示状態、`useRef`は送信中のフラグ、`async/await`はAPIの完了待ちに使っています。
確認画面で住所を直す場合は「入力内容に戻る」から編集し、改めて最新金額を取得します。

## テスト範囲

- Jest：UT-WEB-001〜010の10ケースに対応。004を裾上げあり・なしの2通りで実行して11件。
- 補足5件：決済失敗、注文の通信途絶、受取前の支払選択不可、空カート、数量変更時の裾上げ維持。
- 合計 **16件**。HTTP応答を差し替えた画面の単体テストであり、実MySQLの結合テストとは別。
- 検証環境で `npm test` 16件、`npm run typecheck`、`npm run build` が合格。
- 本番ビルドのNext.jsとHTTP応答を返す模擬APIを起動し、商品取得・カート・購入確認・注文・注文照会の中継と、HttpOnlyのSet-Cookie/Cookieの受け渡しを確認。実DBのテストではない。
- 検証用Chromiumの取得がタイムアウトしたため、ブラウザでの通し操作と見た目は未確認。上記の手順で本人PCで確認する。
- Backendは変更せず、既存の `pytest` は **94 passed, 2 skipped** を確認。IT15件は今回の環境では実行していない。
- CIにはNode.js 24、Jest、型チェック、Next.jsビルドを設定。GitHub上の実行結果はPR後に確認する。

## 現時点の制限

- 模擬Wallet。実際の決済事業者へは接続しない。
- ゲスト購入のみ。会員ログイン・会員購入は未実装。
- Backendの決済再試行、Webhook、UNKNOWNの定期照会、APIの冪等キーは未実装。
- UNKNOWNは「確認中」と表示し、成功扱い・自動再注文はしない。「再取得」はDBの現在状態を読むだけでWalletへ照会しない。
- 注文POSTの通信途絶・5xxは結果不明として扱い、その画面で再送を止める。複数タブ・再読み込みをまたぐ重複注文の保証はBackendの冪等キー実装が必要。
- 注文照会CookieはBackendの仕様どおり直近1件分。新たな注文後は前の注文を照会できない。
- 配送予定日は既存Backendの土日除外。祝日カレンダーは未実装。
- 商品写真は未登録。色やサイズはAPIの選択肢を表示する。
- Azure対応・公開運用の安全性・ST全件・UAT全件の完了を示すものではない。

## Gitと提出

このパッケージは `frontend/` と `.github/workflows/ci.yml` のみです。Backend・SQL・repo直下READMEは上書きしません。
動作確認後、repo直下で以下を実行します。

```powershell
git add frontend .github/workflows/ci.yml
git diff --cached --stat
git commit -m "Add purchase UI and UT-WEB tests"
git push -u origin feature/purchase-ui
```

PR例：`購入画面とUT-WEB-001〜010（商品・カート・購入確認・注文結果）`。
本文には本人PCのJest・build・画面操作の結果を記載。CI合格を確認してからマージします。
rootのREADME・第7版マニュアルには、本人PCで確認した結果と予定変更（9/30ローカル、10/7レビュー、10/14デプロイ）を次の文書更新で反映します。

参考：Next.js公式 [Jest](https://nextjs.org/docs/app/guides/testing/jest) / [rewrites](https://nextjs.org/docs/app/api-reference/config/next-config-js/rewrites)
