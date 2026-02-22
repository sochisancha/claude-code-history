---
name: history
description: 過去のClaudeセッションを一覧・プレビューし、resumeコマンドで再開するブラウザ
user_invocable: true
---

# Session Browser

過去のClaudeセッションを要約付きカード形式で一覧表示し、選択したセッションをresumeで再開するスキル。

## フロー

### Step 1: セッション一覧を表示

以下のコマンドを Bash で実行:

```
python3 ~/.claude/skills/history/scripts/list-sessions.py
```

出力をそのままユーザーに表示する。ただし以下の特殊行はユーザーに見せず内部で保持する:
- `__MAPPING__` で始まるJSON行 → セッション番号→IDのマッピング
- `__NEEDS_SUMMARY__` で始まるJSON行 → 要約未生成のセッションIDリスト

### Step 2: 要約未生成セッションの要約を生成

`__NEEDS_SUMMARY__` がある場合、以下を実行:

1. 要約生成用の要点を抽出する:
```
python3 ~/.claude/skills/history/scripts/extract-for-summary.py <sessionId1> <sessionId2> ...
```

2. 出力された各セッションの要点を読み、それぞれ100文字程度の日本語要約を生成する。

3. Bash で保存スクリプトを実行してキャッシュに追加する:
```
python3 ~/.claude/skills/history/scripts/save-summaries.py <sessionId1> "要約テキスト1" <sessionId2> "要約テキスト2" ...
```

4. 要約が生成できたら、Step 1 の出力の `📋 (要約未生成)` 部分を生成した要約で置き換えて、完全な一覧をユーザーに再表示する。

### Step 3: ユーザーの操作

ユーザーに「番号を入力してセッションを選択してください（`--count 20` で件数変更可、`--all` で短いセッションも表示）」と案内する。

ユーザーが番号を入力したら、マッピングからセッションIDを取得し、以下を実行する:

1. セッションの詳細な文脈を取得:
```
python3 ~/.claude/skills/history/scripts/extract-for-summary.py --detail <sessionId>
```

2. 取得した内容をもとに、そのセッションで何をしていたか・最後にどこまで進んだか・次にやるべきことを200〜300文字程度の日本語で「文脈サマリー」としてまとめる。

3. 以下の形式でユーザーに表示する:

```
## セッション文脈

（生成した文脈サマリー）

## 再開コマンド

claude --resume <sessionId>

再開後、上の文脈サマリーを貼り付ければスムーズに続きから始められます。
```
