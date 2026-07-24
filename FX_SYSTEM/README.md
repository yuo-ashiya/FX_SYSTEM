# 通貨ペア モニタリング(GitHub Pages版)

USD/JPY, EUR/JPY, GBP/JPY, AUD/JPY, EUR/USD, GBP/USD, AUD/USD, EUR/GBP,
CHF/TRY, TRY/JPY, CHF/MXN, MXN/JPY の現在値を表示し、手動設定したアラート上限/下限を
超えると背景色が変わります(上限超え=赤、下限割れ=青)。

## 仕組み

- **GitHub Actions**が15分おきに自動実行され、Python(yfinance)でレートを取得して
  `rates.json` を更新・コミットします(自宅PC不要、GitHubのサーバー上で動きます)
- **GitHub Pages**は `index.html` と `rates.json` を配信するだけの静的サイトです。
  スリープや起動待ちが一切なく、開けば即座に表示されます
- アラート上限/下限は、開いたスマホ・ブラウザの中(localStorage)に保存されます。
  そのため **その端末・そのブラウザだけ** に保存され、他の端末とは同期されません
  (1台のスマホでブックマークして使う想定なら問題ありません)

## セットアップ手順

### 1. GitHubリポジトリを作成

1. https://github.com で無料アカウントを作成(既にあればスキップ)
2. 新規リポジトリを作成(例: `fx-monitor`、**Public**にしてください。Privateだと
   Pagesが無料で使えない場合があります)

### 2. ファイルをアップロード

このフォルダの中身をすべて、リポジトリのルートにそのままアップロードしてください。
フォルダ構成を維持するのがポイントです(`.github/workflows/update-rates.yml` も含む)。

```
(リポジトリのルート)
├── index.html
├── rates.json          ← 初回のサンプルデータ。Actionsが実行されると自動更新されます
├── fetch_rates.py
├── requirements.txt
└── .github/
    └── workflows/
        └── update-rates.yml
```

GitHubのWeb画面でアップロードする場合、"Add file" → "Upload files" で
`.github` フォルダごとドラッグ&ドロップすればフォルダ構成ごと反映されます。
(うまく反映されない場合は、GitHub Desktopや `git` コマンドでのpushをおすすめします)

### 3. GitHub Pagesを有効化

1. リポジトリの **Settings** → 左メニューの **Pages**
2. "Build and deployment" の Source を **Deploy from a branch** に設定
3. Branch を `main` / フォルダを `/ (root)` にして **Save**
4. 数分待つと `https://(あなたのユーザー名).github.io/fx-monitor/` のようなURLが有効になります

### 4. Actionsを有効化・初回実行

1. リポジトリの **Actions** タブを開く
2. 初回は "I understand my workflows, go ahead and enable them" のような確認が出るので許可
3. "Update FX Rates" ワークフローを選び、**Run workflow** ボタンで手動実行(初回はこれで
   `rates.json` を最新化しておくとスムーズです)
4. 以降は `cron: '*/15 * * * *'` の設定により自動で15分おきに実行されます

### 5. スマホで開く

- 2で発行されたURLをスマホのホーム画面に追加しておけば、タップ一つで開けます
- ページを開くたびに最新の `rates.json` を取得します(常時接続しっぱなしにする必要はありません)

---

## 注意点

- **更新頻度**: 15分おきの取得です。tick単位のリアルタイム性はありませんが、
  1時間に1回程度の確認用途には十分です。もっと頻繁にしたい場合は
  `update-rates.yml` の cron を `*/5 * * * *` 等に変更できますが、GitHub Actionsの
  スケジュール実行は仕組み上、混雑時に数分遅れることがあります。
- **アラート設定の保存範囲**: 前述の通りブラウザのlocalStorageに保存されるため、
  スマホを変えたりブラウザのデータを消去すると設定は消えます。複数端末で共有したい
  場合は別途サーバー側保存の仕組みが必要になるので、必要であれば拡張します。
- **公開リポジトリ**: 通貨レートの数値自体は機密情報ではありませんが、リポジトリを
  Publicにするとコード・データが誰でも閲覧できる状態になります。気になる場合は
  Private + GitHub Pro(Pagesが使える有料プラン)を検討してください。

## カスタマイズ

- `fetch_rates.py` 内の `PAIRS` / `BASE_TICKERS` / `compute_pairs()` で
  対象通貨ペアを追加・変更できます
- `index.html` 内の `DECIMALS` で表示桁数を調整できます
