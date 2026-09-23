---
name: solo-loop
display_name: SOLO-LOOP 长循环任务驱动器
display_name_en: SOLO-LOOP Long-Horizon Autonomous Runner
description: 把长期目标跑成无人值守、可断点续跑、抗限流的多轮长循环任务：状态全落盘、惰性分层拆解、子任务隔离执行、父会话永不膨胀。当用户说「长循环」「自动跑到底」「无人值守」「拆任务自己干」「长周期项目」时使用。
description_zh: 把长期目标变成无人值守、可断点续跑、抗限流的长循环任务机器，状态全落盘、子任务隔离执行、父会话永不膨胀。
description_en: Turn long-horizon goals into unattended, resumable, rate-limit-resilient autonomous loops with disk-backed state and isolated subtasks.
category: productivity
version: 3.0.0
author: yu-1018
license: MIT
allowed-tools: bash, read, write, edit
---

# SOLO-LOOP · 长循环任务驱动器

把「一个大目标」变成一台**无人值守、可断点续跑、永不上下文爆炸、且抗限流**的机器。

## 它解决什么

1. **长任务跑不完** → 状态全落盘 + 定时唤醒，进程崩了/机器重启都能接着跑，不依赖记忆。
2. **上下文爆炸** → 父会话只当调度器，子任务一律隔离执行、只回 ≤120 字回执 + 写盘产物，父**永不读产物正文**。
3. **空转烧钱 / 被限流打死** → 显式停机线（预算 / 连续零进展）+ 三层抗限流（降并发 / 冷却门 / 换模型）。

## 60 秒上手

```bash
# 1. 初始化一个循环工作区（用 Bash 工具执行）
python scripts/solo_init.py --root /path/to/my-loop --goal "要什么 + 怎么算成功"

# 2. 建定时任务：schedule 用 templates/cron-payload.json 渲染出的 <root>/cron-payload.json
#    并把返回的 jobId 写进 <root>/state.json 的 cron.jobId

# 3. 随时看进度 / 校验
python scripts/solo_status.py   --root /path/to/my-loop
python scripts/solo_validate.py --root /path/to/my-loop
```

没有定时器的运行时也能用：手动重复「执行一轮」即可（见《每轮流程》），状态机制完全一样。

## 铁律

R1 落盘优先：计划/状态/结论先写文件，再走下一步。
R2 最小读写：每轮只读 `state.json`+本文件+`PROGRESS.md` 末 20 行；**禁止读 `artifacts/` 正文**。
R3 子任务一律隔离执行（`isolated`，禁止 fork）；只认盘上回执，不认对话记忆。
R4 每轮只做两件事：**对账 + 派发**。长推理与干活都不在调度器里做。
R5 派发任务书必须自包含（背景/交付物/输入输出路径/验收/预算/回执格式）。
R6 SOLO 自治：不提问、不等确认，自主决策写 `DECISIONS.md`；只在**真阻断**时上报。
R7 全局并发 = 1：任何时刻最多 1 个在跑的子任务。

## 抗限流（L1–L6）

L1 **并发压到 1**：每轮最多派 `maxLeavesPerTick`（默认 1）；定时任务加 `staggerMs ≥ 30s` 抖动，避免整点齐发。
L2 **冷却门**：派发前看 `state.rateLimit`；`cooldownUntil > now` → 本轮只对账不派发，**且不计零进展**。
L3 **429 ≠ 失败**：命中限流 → 节点回 `ready`、`attempts` 不 +1，写 `cooldownUntil = now + base×2^count + jitter`（base 60s，封顶 30min）。
L4 **多模型降级**：`state.models=[主,备1,备2]`；当前模型限流/不可用 → 顺位切换，回写 `lastModel`/`switches`；全挂才冷却。
L5 **限流 ≠ 零进展**：`noProgressStreak` 仅在「无派发、无结清、且无任何 ready 可派」时才 +1。
L6 **子任务内也限流**：任务书要求串行不并发、批量写盘、尊重 `Retry-After`、单会话外部调用 ≤ `maxSubCallsPerLeaf`；超了回 `TOO_BIG`。

## 文件契约

```
<LOOP_ROOT>/
  INSTRUCTION.md        驱动器指令（只读，每轮读它）
  state.json            任务树+状态+预算+限流+游标（唯一机器事实源）
  PROGRESS.md           人读进度（append-only，每轮一行）
  DECISIONS.md          自主决策（append-only）
  REPORT.md             终报告（收尾写）
  runs/<nodeId>.json    子任务回执（子任务写，父只判存在性+读摘要）
  artifacts/...         叶子产物（子任务写）
  templates/leaf-brief.md
  archive/...           历史快照
```

## 任务树

1. 根节点固定 `id="0" kind="goal"`；其余层级点号 `1 / 1.2 / 1.2.1`，登记进父节点 `children`。
2. kind：`goal`（仅根）/`group`（待展开）/`leaf`（可派发）；状态机 `pending→ready→running→done|blocked|failed`。
3. 惰性展开：`group` 只在 `deps` 全满足时才展开，禁止一次拍平整棵树。
4. **叶子判据（硬）**：1 次子会话能做完 = ≤15 分钟 + ≤1 交付物 + 步骤 ≤3 + 零人工输入。超标继续拆。

## 每轮流程

1. 读 `state.json`；若只有根节点 → **阶段 0**：拆 L1（3–7 个 group）落盘，结束本轮。
2. **对账** running 节点：DONE 且产物在 → `done`；BLOCKED → 记因（缺凭证则上报）；TOO_BIG → 按 `next` 建议拆；超时（>3×`maxLeafMinutes`）→ `attempts+1`，超 `maxRetries` → `failed` 否则 `ready`；限流 → 按 L3。
3. **结算**：`deps` 全 `done` 的 `pending` → `ready`。
4. **展开**：`deps` 全 `done` 的 `group` → 展开子节点。
5. **派发**：取 `ready` 叶子 ≤`maxLeavesPerTick`，按 `templates/leaf-brief.md` 渲染任务书 → 隔离子会话，taskName = 节点 id 把 `.` 换 `-`。
6. **落盘**：写 `state.json`；`PROGRESS.md` 追加一行；有决策写 `DECISIONS.md`；按 L5 更新 `noProgressStreak`。
7. **终止判定** + ≤3 行摘要（派发数/结清数/下一步）。

## 终止与收尾

- **完成**：所有 `leaf` 均 `done` 且无 `pending/ready/running` → `status="done"`。
- **停机**：`tick ≥ maxTicks`，或 `noProgressStreak ≥ maxNoProgressTicks`，或只剩 `blocked` 且无 `ready|running` → `status="halted"`。
- **收尾动作**：写 `REPORT.md`（逐叶子 状态/回执摘要/产物路径）→ 跑 `python scripts/solo_validate.py --root <LOOP_ROOT>` 自检 → 顶层置终态 → **删掉自己的定时任务** → `PROGRESS.md`/`DECISIONS.md` 各记一条。`halted` 时摘要必须写清「卡在哪、缺什么、要人做什么」。

## 不同运行时的装载方式

1. **有定时器**：每 N 分钟唤醒一个隔离会话，消息 = 「读 `<LOOP_ROOT>/INSTRUCTION.md`，执行本轮 tick，只回 ≤3 行」。
2. **只能手动**：对 AI 说「跑一轮 solo-loop」，等价于 tick 一次。
3. **无子代理能力**：把任务书写进 `runs/<id>.task.md`，由人/AI 在另一会话执行并写回执，协议不变。

## 配套文件

`scripts/` 初始化与校验脚本 ｜ `templates/` 状态/任务书/定时任务模板 ｜ `@references/LIMITS.md` 限流手册 ｜ `@references/RUNBOOK.md` 运维与故障恢复 ｜ `@references/examples.md` 目标写法示例。
