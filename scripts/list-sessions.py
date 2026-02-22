#!/usr/bin/env python3
"""過去のClaudeセッションをカード形式で一覧表示する（キャッシュ要約対応）。"""

import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

CACHE_FILE = os.path.expanduser("~/.claude/skills/history/cache/summaries.json")


def load_summaries_cache():
    """キャッシュされた要約を読み込む。"""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def clean_topic(text):
    """トピックからシステムタグを除去してクリーンなテキストを返す。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def get_duration_seconds(first_ts_str, last_ts_str):
    """2つのISO タイムスタンプ間の秒数を返す。"""
    if not first_ts_str or not last_ts_str:
        return 0
    try:
        start = datetime.fromisoformat(first_ts_str.replace("Z", "+00:00"))
        end = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00"))
        return int((end - start).total_seconds())
    except (ValueError, TypeError):
        return 0


def parse_session(filepath):
    """セッションJSONLファイルをパースして要約情報を返す。"""
    session_id = os.path.basename(filepath).replace(".jsonl", "")
    file_size = os.path.getsize(filepath)
    first_timestamp = None
    last_timestamp = None
    first_user_message = None
    user_count = 0
    assistant_count = 0
    tools = set()

    try:
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
                ts = row.get("timestamp")

                if row_type == "user":
                    user_count += 1
                elif row_type == "assistant":
                    assistant_count += 1

                if ts and row_type in ("user", "assistant"):
                    if first_timestamp is None:
                        first_timestamp = ts
                    last_timestamp = ts

                if row_type == "user" and first_user_message is None:
                    content = row.get("message", {}).get("content", "")
                    if isinstance(content, str):
                        candidate = clean_topic(content)
                    elif isinstance(content, list):
                        texts = []
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                texts.append(item.get("text", ""))
                            elif isinstance(item, str):
                                texts.append(item)
                        candidate = clean_topic(" ".join(texts))
                    else:
                        candidate = ""
                    skip_patterns = [
                        "Caveat:", "Request interrupted",
                        "[Request interrupted", "No response requested",
                        "command-name", "command-message",
                        "Implement the following plan:",
                    ]
                    is_slash_cmd = bool(re.match(r"^/\w+\s+\w+\s*$", candidate))
                    if (candidate and len(candidate) > 1
                            and not any(p in candidate for p in skip_patterns)
                            and not is_slash_cmd):
                        first_user_message = candidate

                if row_type == "assistant":
                    content = row.get("message", {}).get("content", [])
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "tool_use":
                                name = item.get("name", "")
                                if name.startswith("mcp__"):
                                    parts = name.split("__")
                                    if len(parts) >= 2:
                                        name = parts[1]
                                tools.add(name)
    except (OSError, IOError):
        return None

    message_count = user_count + assistant_count
    if message_count == 0:
        return None

    topic = (first_user_message or "").strip()
    if len(topic) > 80:
        topic = topic[:77] + "..."

    return {
        "session_id": session_id,
        "timestamp": first_timestamp,
        "last_timestamp": last_timestamp,
        "user_count": user_count,
        "assistant_count": assistant_count,
        "message_count": message_count,
        "tools": sorted(tools),
        "file_size": file_size,
        "topic": topic,
    }


def format_datetime_range(first_ts_str, last_ts_str):
    """開始〜終了を YYYY/MM/DD HH:MM ~ HH:MM (Xm) 形式で返す。"""
    if not first_ts_str:
        return "不明"
    try:
        start = datetime.fromisoformat(first_ts_str.replace("Z", "+00:00")).astimezone()
        result = start.strftime("%Y/%m/%d %H:%M")
        if last_ts_str:
            end = datetime.fromisoformat(last_ts_str.replace("Z", "+00:00")).astimezone()
            result += f" ~ {end.strftime('%H:%M')}"
            delta = int((end - start).total_seconds())
            if delta < 60:
                result += f" ({delta}s)"
            else:
                hours, remainder = divmod(delta, 3600)
                minutes, _ = divmod(remainder, 60)
                if hours > 0:
                    result += f" ({hours}h{minutes:02d}m)"
                else:
                    result += f" ({minutes}m)"
        return result
    except (ValueError, TypeError):
        return "不明"


MIN_DURATION_SECONDS = 600


def main():
    parser = argparse.ArgumentParser(description="Claude セッション一覧表示")
    parser.add_argument("--count", type=int, default=15, help="表示件数（デフォルト: 15）")
    parser.add_argument("--all", action="store_true", help="短いセッションも含めて表示")
    args = parser.parse_args()

    projects_dir = os.path.expanduser("~/.claude/projects")
    files = glob.glob(os.path.join(projects_dir, "*", "*.jsonl"))

    if not files:
        print("セッションが見つかりません。", file=sys.stderr)
        sys.exit(1)

    summaries = load_summaries_cache()

    sessions = []
    for f in files:
        info = parse_session(f)
        if info:
            sessions.append(info)

    sessions.sort(key=lambda s: s["timestamp"] or "", reverse=True)

    if not args.all:
        sessions = [
            s for s in sessions
            if get_duration_seconds(s["timestamp"], s["last_timestamp"]) >= MIN_DURATION_SECONDS
        ]

    sessions = sessions[: args.count]

    if not sessions:
        print("有効なセッションが見つかりません。", file=sys.stderr)
        sys.exit(1)

    mapping = {}
    needs_summary = []

    for i, s in enumerate(sessions, 1):
        sid = s["session_id"]
        dt_range = format_datetime_range(s["timestamp"], s["last_timestamp"])
        msg = f"user {s['user_count']} / assistant {s['assistant_count']}"
        tools_str = ", ".join(s["tools"]) if s["tools"] else "なし"
        topic = s["topic"] if s["topic"] else ""
        summary = summaries.get(sid, "")

        print(f"#{i}  {topic}")
        print(f"  日時: {dt_range}  |  メッセージ: {msg}  |  ツール: {tools_str}")
        if summary:
            print(f"  📋 {summary}")
        else:
            print(f"  📋 (要約未生成)")
        print()
        mapping[str(i)] = sid
        if not summary:
            needs_summary.append(sid)

    print(f"__MAPPING__{json.dumps(mapping)}")
    if needs_summary:
        print(f"__NEEDS_SUMMARY__{json.dumps(needs_summary)}")


if __name__ == "__main__":
    main()
