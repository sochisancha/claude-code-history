# /history - Claude Code セッション履歴ブラウザ

Claude Code の過去のセッション（会話）を一覧表示し、選んだセッションをすぐに再開できるスキルです。

## これは何？

Claude Code で作業していると、「あの時の続きをやりたい」「前に何を話したっけ？」ということがよくあります。

`/history` を使えば：

1. 過去のセッションが **要約付きの一覧** で表示される
2. 番号を選ぶと **文脈サマリー**（何をしていたか・どこまで進んだか）が表示される
3. 表示された **`claude --resume` コマンド** をコピペするだけで、そのセッションの続きから再開できる

## 使い方

Claude Code で `/history` と入力するだけ。

```
> /history
```

一覧が表示されたら番号を入力して選択。再開用のコマンドが表示されます。

### オプション

| オプション | 説明 |
|-----------|------|
| `--count 20` | 表示件数を変更（デフォルト: 15件） |
| `--all` | 10分未満の短いセッションも表示 |

## 表示される情報

各セッションには以下の情報が表示されます：

- **タイトル** - 最初のユーザーメッセージから自動生成
- **日時** - 開始〜終了時刻と所要時間
- **メッセージ数** - ユーザーとアシスタントの発言数
- **使用ツール** - そのセッションで使われたツール一覧
- **要約** - AIが生成した100文字程度の日本語要約

## 仕組み

### ファイル構成

```
~/.claude/skills/history/
├── SKILL.md                          # スキル定義（Claude Codeが読む手順書）
├── README.md                         # このファイル
├── scripts/
│   ├── list-sessions.py              # セッション一覧を生成
│   ├── extract-for-summary.py        # セッションの要点を抽出
│   ├── save-summaries.py             # 要約をキャッシュに保存
│   └── show-session.py               # セッション詳細を表示
└── cache/
    └── summaries.json                # 生成済み要約のキャッシュ
```

### 処理の流れ

```
/history 実行
    ↓
① list-sessions.py がセッションログ(.jsonl)を読み取り、一覧を生成
    ↓
② 要約が未生成のセッションがあれば：
   extract-for-summary.py で要点を抽出 → AIが要約を生成 → save-summaries.py でキャッシュに保存
    ↓
③ ユーザーが番号を選択
    ↓
④ extract-for-summary.py --detail で詳細な文脈を抽出
    ↓
⑤ AIが文脈サマリーを生成し、claude --resume コマンドと一緒に表示
```

### フィルタリング

- **10分未満のセッション** はデフォルトで非表示（短すぎるセッションはノイズになるため）
- `--all` オプションで全セッションを表示可能

### 要約キャッシュ

- 一度生成した要約は `cache/summaries.json` に保存される
- 次回以降は再生成せず、キャッシュから読み込むので高速
- セッションIDをキーとしたシンプルなJSONファイル

## インストール

1. このリポジトリを `~/.claude/skills/history/` に配置

```bash
git clone https://github.com/sochisancha/claude-code-history.git ~/.claude/skills/history
```

2. Claude Code で `/history` と入力すれば使えます

### 必要なもの

- Claude Code（Anthropic公式CLI）
- Python 3.8以上（macOS標準で入っています）

### 注意事項

- `list-sessions.py` 内のセッションディレクトリパスがハードコードされています（`~/.claude/projects/-Users-sochi`）。別のユーザー名の場合は書き換えが必要です。

## ライセンス

MIT
