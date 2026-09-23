#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""solo-loop 校验：state.json 结构 + 任务树完整性 + 回执/产物对账 + REPORT 自检。

用法: python solo_validate.py --root ./my-loop
退出码: 0=通过（可能有警告）  1=有错误
"""
import argparse
import json
import pathlib
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

REQUIRED_TOP = ["goal", "status", "budget", "cursor", "nodes"]
VALID_STATUS = {"pending", "ready", "running", "done", "blocked", "failed"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    a = ap.parse_args()
    root = pathlib.Path(a.root).expanduser().resolve()
    errors, warns = [], []

    p = root / "state.json"
    if not p.exists():
        print(f"[X] 缺少 {p}")
        return 1
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"[X] state.json 不是合法 JSON: {e}")
        return 1

    for k in REQUIRED_TOP:
        if k not in st:
            errors.append(f"state.json 缺少顶层字段 `{k}`")

    nodes = {}
    for n in st.get("nodes", []):
        if "id" in n:
            if n["id"] in nodes:
                errors.append(f"节点 id 重复: {n['id']}")
            nodes[n["id"]] = n
        else:
            errors.append("存在没有 id 的节点")

    if "0" not in nodes:
        errors.append("缺少根节点 id=\"0\"")
    else:
        if nodes["0"].get("kind") != "goal":
            errors.append("根节点 kind 必须是 goal")
        if nodes["0"].get("deps"):
            warns.append("根节点 deps 建议为空")

    for nid, n in nodes.items():
        stt = n.get("status")
        if stt not in VALID_STATUS:
            errors.append(f"节点 {nid} 状态非法: {stt}")
        for d in n.get("deps", []):
            if d not in nodes:
                errors.append(f"节点 {nid} 依赖不存在的节点 {d}")
        for c in n.get("children", []):
            if c not in nodes:
                errors.append(f"节点 {nid} 的子节点 {c} 未在 nodes 中登记")
            elif nid not in nodes[c].get("deps", []) and nodes[c].get("parent") is None:
                pass  # parent 字段可选
        if nid != "0" and "." not in nid:
            warns.append(f"节点 {nid} 不是层级点号 id（建议 1 / 1.2 / 1.2.1）")

    # 环检测
    seen, stack = set(), set()

    def dfs(x):
        if x in stack:
            errors.append(f"依赖存在环，涉及节点 {x}")
            return
        if x in seen:
            return
        stack.add(x)
        for d in nodes.get(x, {}).get("deps", []):
            if d in nodes:
                dfs(d)
        stack.discard(x)
        seen.add(x)

    for nid in nodes:
        dfs(nid)

    # running 节点是否有回执
    for nid, n in nodes.items():
        if n.get("status") == "running":
            r = root / "runs" / f"{nid}.json"
            if not r.exists():
                warns.append(f"节点 {nid} 仍是 running 但无回执 {r.name}（可能超时未收）")

    # REPORT 自检：文中反引号路径必须存在
    rep = root / "REPORT.md"
    if rep.exists():
        for m in re.findall(r"`([^`\n]+)`", rep.read_text(encoding="utf-8", errors="replace")):
            if re.search(r"[\\/]", m) and not m.startswith(("http", "<")):
                cand = (root / m) if not pathlib.Path(m).is_absolute() else pathlib.Path(m)
                if not cand.exists():
                    errors.append(f"REPORT.md 引用的路径不存在: {m}")

    print(f"节点数: {len(nodes)}  |  错误: {len(errors)}  |  警告: {len(warns)}")
    for e in errors:
        print("  [X] " + e)
    for w in warns:
        print("  [!] " + w)
    if not errors:
        print("[ok] 校验通过")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
