#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""solo-loop 进度查看：任务树、状态统计、预算、限流冷却、最近进度。

用法: python solo_status.py --root ./my-loop [--progress-lines 12]
"""
import argparse
import datetime
import json
import pathlib
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MARK = {"done": "[x]", "running": "[~]", "ready": "[ ]", "pending": "[ ]",
        "blocked": "[!]", "failed": "[X]"}


def load(root: pathlib.Path) -> dict:
    p = root / "state.json"
    if not p.exists():
        print(f"[!] 找不到 {p}")
        raise SystemExit(2)
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--progress-lines", type=int, default=12)
    a = ap.parse_args()
    root = pathlib.Path(a.root).expanduser().resolve()
    st = load(root)

    nodes = {n["id"]: n for n in st.get("nodes", [])}
    cur = st.get("cursor", {})
    rl = st.get("rateLimit", {})
    bud = st.get("budget", {})

    print(f"目标 : {st.get('goal')}")
    print(f"状态 : {st.get('status')}   轮次: {cur.get('tick')}/{bud.get('maxTicks')}   "
          f"零进展: {cur.get('noProgressStreak')}/{bud.get('maxNoProgressTicks')}")
    cd = rl.get("cooldownUntil")
    if cd:
        try:
            left = (datetime.datetime.fromisoformat(str(cd)) - datetime.datetime.now().astimezone())
            print(f"限流 : 冷却中，剩余约 {int(left.total_seconds())}s（count={rl.get('count')}, 已换模型 {rl.get('switches')} 次）")
        except Exception:
            print(f"限流 : cooldownUntil={cd}")
    else:
        print("限流 : 正常")

    counts = {}
    for n in nodes.values():
        counts[n.get("status", "?")] = counts.get(n.get("status", "?"), 0) + 1
    print("统计 : " + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print("")

    def walk(nid, depth):
        n = nodes.get(nid)
        if not n:
            return
        print(f"  {'  ' * depth}{MARK.get(n.get('status'), '[?]')} {nid:<10} {n.get('kind',''):<6} "
              f"{n.get('status',''):<8} {n.get('title','')}")
        for c in n.get("children", []):
            walk(c, depth + 1)

    print("任务树:")
    walk("0", 0)

    pg = root / "PROGRESS.md"
    if pg.exists():
        lines = pg.read_text(encoding="utf-8", errors="replace").splitlines()
        print("\n最近进度:")
        for ln in lines[-a.progress_lines:]:
            print("  " + ln)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
