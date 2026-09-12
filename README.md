# GU ECサイト — V字モデル開発演習（Lv3）

Tech0 個人宿題。GU の EC サイトを題材に、要求 → 要件 → 設計 → テスト設計 → 実装 → テスト → デプロイ を一通り実施する。

作成者：平田真子（12期）

## 主題

実機調査（2026/8/27・約2時間）で観察した2つの課題を主題とする。

| # | 課題 | 対応する要求群 |
| --- | --- | --- |
| 1 | 裾上げの可否・料金・追加日数が、購入判断を行う画面で分からない | REQ-FR-301〜313 |
| 2 | 購入手続きの入力負荷が高く、購入が中断する | ウォレット決済の要求群 |

網羅層として EC サイトに必要な機能を定義しているが、実装とテストの対象は
**「裾上げを指定し、内容を確認して Wallet 決済で購入する」経路**に絞る。

## 前提条件（変更不可）

- Web アプリケーションとしてブラウザから利用する
- フロントエンド：Next.js ／ バックエンド：FastAPI
- インフラ：Microsoft Azure（DB は Azure Database for MySQL Flexible Server）
- バックエンドを動かす Azure サービスは非機能要求を満たす前提で選定する
- Vercel・Streamlit は使用しない（Week7 デプロイ時）
- テストフレームワークは pytest（Backend）／ Jest（Frontend）

## 進捗

| ゲート | 期限 | 状態 | 成果物 |
| --- | --- | --- | --- |
| 要求仕様書 | Week1 | 完了（GUEC-REQ-01） | `docs/01_要求仕様書/` |
| 要件定義書 | Week2 | 完了（GUEC-RD-01） | `docs/02_要件定義書/` |
| 設計仕様書 | Week3（9/2） | 完了。STEP11 まで未決事項を解消 | `docs/03_設計仕様書/` |
| テスト仕様書 | Week4（9/9） | 完了（GUEC-TD-01 v1.0）。UT58／IT40／ST16／UAT6＝120行、全件未実行 | `docs/04_テスト仕様書/` |
| コーディング＋単体テスト | Week5（9/16） | 着手（リポジトリ・CI 構築済み、実装は未着手） | `backend/` `frontend/` |
| コードレビュー | Week6（9/23） | 未着手 | 同 Lv 間ローテーション |
| Azure デプロイ | Week7（9/30） | 未着手 | CI に単体テストを組み込む |
| セキュリティチェック | Week8（10/7） | 未着手 | — |
| ログ・アラート | Week9（10/14） | 未着手 | — |
| 閉域化 | Week10（10/21） | 未着手 | — |

## フォルダ構成

```
.
├── .github/workflows/ci.yml   … Backend/Frontend のテスト自動実行
├── backend/                   … FastAPI（未実装）
│   ├── requirements.txt
│   └── tests/                 … pytest
├── frontend/                  … Next.js（Week5 で作成）
└── docs/
    ├── 01_要求仕様書/
    ├── 02_要件定義書/
    ├── 03_設計仕様書/
    └── 04_テスト仕様書/
```

## ドキュメントとコードの対応

テスト仕様書の ID 体系をコードでもそのまま使う。

```
要求 REQ-FR-xxx ─→ 要件 F-xxx / NFR-S-xx ─→ TM-xx ─→ ケースID（UT-CALC-001 等）
```

テスト関数名にケース ID を含め、どの要求を確認しているか追えるようにする。

```python
def test_UT_CALC_001_合計と内税():
    ...
```

## ブランチ運用

| ブランチ | 用途 |
| --- | --- |
| `main` | 常にテストが通る状態を保つ。直接コミットしない |
| `feature/<対象>` | 実装単位。例 `feature/ut-calc`、`feature/hem-input` |

1. `main` から `feature/xxx` を切る
2. 作業してコミット
3. Pull Request を作成（CI が自動で走る）
4. CI が緑になったらマージし、ブランチを削除

Pull Request には、対応するテストケース ID（例：UT-CALC-001〜003）を書く。

## テストの実行

### Backend（pytest）

```bash
cd backend
pip install -r requirements.txt
pytest
```

### Frontend（Jest）

Week5 で Next.js プロジェクトを作成後に有効化する。
CI は `frontend/package.json` が存在するときだけ Frontend のテストを実行する。


