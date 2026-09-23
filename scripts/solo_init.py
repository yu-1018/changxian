#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""solo-loop 初始化：建工作区 → 写 state.json → 渲染驱动器指令 → 打印下一步。

用法:
  python solo_init.py --root ./my-loop --goal "要什么 + 怎么算成功"
可选:
  --title "短标题" --max-ticks 200 --interval-min 10 --models "主模型,备用模型" --force
"""
import argparse
import datetime
import json
import pathlib
import shutil
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
TPL = SKILL_DIR / "templates"

PROGRESS_HEAD = "# PROGRESS\n\n| 轮次 | 时间 | 事件 | 节点 | 备注 |\n|---|---|---|---|---|\n"
DECISIONS_HEAD = "# DECISIONS\n\nSOLO 自主决策记录（append-only）。\n\n"


def render(text: str, mapping: dict) -> str:
    for k, v in mapping.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description="solo-loop 初始化")
    ap.add_argument("--root", required=True, help="循环工作区目录")
    ap.add_argument("--goal", required=True, help="目标：要什么 + 成功判据")
    ap.add_argument("--title", default=None, help="目标短标题（默认截取 goal 前 40 字）")
    ap.add_argument("--max-ticks", type=int, default=200)
    ap.add_argument("--interval-min", type=int, default=10)
    ap.add_argument("--models", default="", help="逗号分隔的模型降级链，如 'gpt-4o,claude-sonnet'")
    ap.add_argument("--force", action="store_true", help="已存在时覆盖 state.json")
    args = ap.parse_args()

    root = pathlib.Path(args.root).expanduser().resolve()
    state_path = root / "state.json"
    if state_path.exists() and not args.force:
        print(f"[!] 已存在 {state_path}，未改动。要重来请加 --force（会重置状态，产物保留）。")
        return 2

    for d in ("runs", "artifacts", "archive", "templates"):
        (root / d).mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    title = args.title or (args.goal[:40] + ("…" if len(args.goal) > 40 else ""))
    models = [m.strip() for m in args.models.split(",") if m.strip()]

    # state.json
    st = json.loads((TPL / "state.template.json").read_text(encoding="utf-8"))
    st["goal"] = args.goal
    st["createdAt"] = now
    st["budget"]["maxTicks"] = args.max_ticks
    st["models"] = models or st["models"]
    st["nodes"][0]["title"] = title
    state_path.write_text(json.dumps(st, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # 驱动器指令
    mapping = {"LOOP_ROOT": str(root)}
    (root / "INSTRUCTION.md").write_text(
        render((TPL / "driver-prompt.template.md").read_text(encoding="utf-8"), mapping),
        encoding="utf-8")
    shutil.copyfile(TPL / "leaf-brief.template.md", root / "templates" / "leaf-brief.md")

    # 人读文件
    if not (root / "PROGRESS.md").exists():
        (root / "PROGRESS.md").write_text(PROGRESS_HEAD, encoding="utf-8")
    if not (root / "DECISIONS.md").exists():
        (root / "DECISIONS.md").write_text(DECISIONS_HEAD, encoding="utf-8")

    # 定时任务 payload（供 agent 用 cron 工具创建）
    payload = json.loads((TPL / "cron-payload.json").read_text(encoding="utf-8"))
    payload.pop("_comment", None)
    payload["schedule"]["everyMs"] = args.interval_min * 60_000
    payload["payload"]["message"] = render(payload["payload"]["message"], mapping)
    (root / "cron-payload.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[ok] 工作区就绪：{root}")
    print(f"     目标：{args.goal}")
    print("")
    print("下一步：")
    print(f"1. 让 agent 按 {SKILL_DIR / 'SKILL.md'} 创建定时任务（payload 见 {root / 'cron-payload.json'}），")
    print(f"   间隔 {args.interval_min} 分钟；把返回的 jobId 写进 state.json 的 cron.jobId。")
    print(f"2. 进度：python {SKILL_DIR / 'scripts' / 'solo_status.py'} --root \"{root}\"")
    print(f"3. 校验：python {SKILL_DIR / 'scripts' / 'solo_validate.py'} --root \"{root}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
