#!/usr/bin/env python3
"""セッションからAI要約用の要点を抽出する。複数セッションID対応。"""

import glob
import json
import os
import re
import sys


def find_session_file(session_id):
    """全プロジェクトディレクトリからセッションファイルを探す。"""
    projects_dir = os.path.expanduser("~/.claude/projects")
    matches = glob.glob(os.path.join(projects_dir, "*", f"{session_id}.jsonl"))
    return matches[0] if matches else os.path.join(projects_dir, f"{session_id}.jsonl")


def clean_text(text):
    """システムタグ等を除去。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def extract_text(content):
    """メッセージ content からテキスト部分を抽出。"""
    if isinstance(content, str):
        return clean_text(content)
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
            elif isinstance(item, str):
                texts.append(item)
        return clean_text(" ".join(texts))
    return ""


def extract_tools(content):
    """メッセージ content からツール呼び出しを抽出。"""
    if not isinstance(content, list):
        return []
    tools = []
    for item in content:
        if isinstance(item, dict) and item.get("type") == "tool_use":
            tools.append(item.get("name", ""))
    return tools


def extract_session(session_id):
    """セッションから要約用の要点を抽出して出力。"""
    filepath = find_session_file(session_id)

    if not os.path.exists(filepath):
        return f"セッションが見つかりません: {session_id}"

    messages = []  # [(role, text)]

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
            if row_type not in ("user", "assistant"):
                continue

            content = row.get("message", {}).get("content", "")
            text = extract_text(content)
            tools = extract_tools(content) if row_type == "assistant" else []

            # ツール呼び出しだけの場合はツール名を記録
            if tools and not text:
                text = f"[ツール使用: {', '.join(tools)}]"
            elif tools and text:
                text = f"{text} [ツール: {', '.join(tools)}]"

            # 空や無意味なメッセージをスキップ
            skip_patterns = [
                "No response requested", "Caveat:", "Launching skill:",
            ]
            if not text or len(text) < 2 or any(p in text for p in skip_patterns):
                continue

            messages.append((row_type, text))

    if not messages:
        return "メッセージなし"

    # 先頭5件 + 末尾5件を抽出（重複排除）
    head = 5
    tail = 5
    total = len(messages)

    if total <= head + tail:
        selected = messages
    else:
        selected = messages[:head] + [("...", f"（中略: {total - head - tail}メッセージ）")] + messages[-tail:]

    lines = []
    for role, text in selected:
        # 各メッセージを150文字に制限
        if len(text) > 150:
            text = text[:147] + "..."
        label = "U" if role == "user" else ("A" if role == "assistant" else "...")
        lines.append(f"[{label}] {text}")

    return "\n".join(lines)


def extract_session_detail(session_id):
    """セッションからresume時に貼り付ける用の詳細な文脈を抽出。"""
    filepath = find_session_file(session_id)

    if not os.path.exists(filepath):
        return f"セッションが見つかりません: {session_id}"

    messages = []

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
            if row_type not in ("user", "assistant"):
                continue

            content = row.get("message", {}).get("content", "")
            text = extract_text(content)
            tools = extract_tools(content) if row_type == "assistant" else []

            if tools and not text:
                text = f"[ツール使用: {', '.join(tools)}]"
            elif tools and text:
                text = f"{text} [ツール: {', '.join(tools)}]"

            skip_patterns = [
                "No response requested", "Caveat:", "Launching skill:",
            ]
            if not text or len(text) < 2 or any(p in text for p in skip_patterns):
                continue

            messages.append((row_type, text))

    if not messages:
        return "メッセージなし"

    # 詳細版: 先頭10件 + 末尾15件（文脈引き継ぎ用）
    head = 10
    tail = 15
    total = len(messages)

    if total <= head + tail:
        selected = messages
    else:
        selected = messages[:head] + [("...", f"（中略: {total - head - tail}メッセージ）")] + messages[-tail:]

    lines = []
    for role, text in selected:
        if len(text) > 300:
            text = text[:297] + "..."
        label = "U" if role == "user" else ("A" if role == "assistant" else "...")
        lines.append(f"[{label}] {text}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("使い方: extract-for-summary.py [--detail] <sessionId1> [sessionId2] ...", file=sys.stderr)
        sys.exit(1)

    args = sys.argv[1:]
    detail_mode = False
    if args[0] == "--detail":
        detail_mode = True
        args = args[1:]

    session_ids = args
    for sid in session_ids:
        print(f"=== SESSION {sid} ===")
        if detail_mode:
            print(extract_session_detail(sid))
        else:
            print(extract_session(sid))
        print()


if __name__ == "__main__":
    main()
