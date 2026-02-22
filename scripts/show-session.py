#!/usr/bin/env python3
"""指定セッションIDの会話詳細をプレビュー表示する。"""

import json
import os
import sys
from datetime import datetime


def parse_timestamp(ts_str):
    """ISO タイムスタンプを datetime に変換。"""
    if not ts_str:
        return None
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def format_duration(start_dt, end_dt):
    """開始〜終了の時間差を人間可読形式で返す。"""
    if not start_dt or not end_dt:
        return "不明"
    delta = end_dt - start_dt
    total_seconds = int(delta.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}s"
    hours, remainder = divmod(total_seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m"


def extract_text(content):
    """メッセージ content からテキスト部分を抽出。"""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return " ".join(texts)
    return ""


def truncate(text, max_len=100):
    """テキストを指定文字数で切り詰め。"""
    text = text.replace("\n", " ").strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def main():
    if len(sys.argv) < 2:
        print("使い方: show-session.py <sessionId>", file=sys.stderr)
        sys.exit(1)

    session_id = sys.argv[1]
    session_dir = os.path.expanduser("~/.claude/projects/-Users-sochi")
    filepath = os.path.join(session_dir, f"{session_id}.jsonl")

    if not os.path.exists(filepath):
        print(f"セッションが見つかりません: {session_id}", file=sys.stderr)
        sys.exit(1)

    # メッセージをパース
    messages = []  # [(role, text, timestamp)]
    tools = set()
    user_count = 0
    assistant_count = 0
    first_ts = None
    last_ts = None

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue

            row_type = row.get("type")
            ts_str = row.get("timestamp")
            ts = parse_timestamp(ts_str)

            if row_type not in ("user", "assistant"):
                continue

            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            content = row.get("message", {}).get("content", "")

            # ツール収集
            if row_type == "assistant" and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        name = item.get("name", "")
                        if name.startswith("mcp__"):
                            parts = name.split("__")
                            if len(parts) >= 2:
                                name = parts[1]
                        tools.add(name)

            # テキスト抽出
            text = extract_text(content)
            if not text.strip():
                continue

            if row_type == "user":
                user_count += 1
                messages.append(("user", text, ts))
            elif row_type == "assistant":
                assistant_count += 1
                messages.append(("asst", text, ts))

    if not messages:
        print("このセッションにはメッセージがありません。", file=sys.stderr)
        sys.exit(1)

    # ヘッダ情報
    start_str = first_ts.astimezone().strftime("%Y/%m/%d %H:%M") if first_ts else "不明"
    end_str = last_ts.astimezone().strftime("%H:%M") if last_ts else "不明"
    duration = format_duration(first_ts, last_ts)
    tools_str = ", ".join(sorted(tools)) if tools else "なし"

    print(f"日時: {start_str} 〜 {end_str} ({duration})")
    print(f"メッセージ数: user {user_count} / assistant {assistant_count}")
    print(f"ツール: {tools_str}")
    print()
    print("── 会話の流れ " + "─" * 50)

    # 先頭3件 + 末尾3件、中間は省略
    show_head = 3
    show_tail = 3
    total = len(messages)

    if total <= show_head + show_tail + 1:
        # 全件表示
        for role, text, _ in messages:
            print(f" {role:<5} │ {truncate(text)}")
    else:
        # 先頭
        for role, text, _ in messages[:show_head]:
            print(f" {role:<5} │ {truncate(text)}")
        # 省略
        skipped = total - show_head - show_tail
        print(f"  ...  │ （省略: {skipped}メッセージ）")
        # 末尾
        for role, text, _ in messages[-show_tail:]:
            print(f" {role:<5} │ {truncate(text)}")

    print("─" * 64)


if __name__ == "__main__":
    main()
