#!/usr/bin/env python3
"""要約をキャッシュファイルにマージ保存する。引数: key1 value1 key2 value2 ..."""

import json
import os
import sys

CACHE_FILE = os.path.expanduser("~/.claude/skills/history/cache/summaries.json")


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2 != 0:
        print("使い方: save-summaries.py <sessionId1> <summary1> [sessionId2 summary2] ...", file=sys.stderr)
        sys.exit(1)

    # 既存キャッシュ読み込み
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass

    # 新しい要約をマージ
    for i in range(0, len(args), 2):
        cache[args[i]] = args[i + 1]

    # 保存
    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    print(f"{len(args) // 2}件の要約を保存しました。")


if __name__ == "__main__":
    main()
