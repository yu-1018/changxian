# RUNBOOK.md · 运维与故障恢复

## 1. 启动

1. `python scripts/solo_init.py --root <LOOP_ROOT> --goal "..."`（可加 `--max-ticks` / `--interval-min` / `--models`）。
2. 让 agent 按 `SKILL.md` 用 `cron` 工具创建定时任务（payload 见 `<LOOP_ROOT>/cron-payload.json`）。
3. **把返回的 jobId 写进 `<LOOP_ROOT>/state.json` 的 `cron.jobId`** —— 否则收尾时只能靠会话键/任务名反推。
4. 手动跑一轮确认：`state.json` 更新、`PROGRESS.md` 多一行、`runs/` 出现记录。

## 2. 调参

| 参数 | 位置 | 建议 |
|---|---|---|
| `maxLeavesPerTick` | `state.json.budget` | 先 1（稳）；跑顺了再 2–3 |
| 间隔 | 定时任务 `everyMs` | 叶子平均 <3min 可缩到 5min |
| `maxTicks` | `state.json.budget` | 兜底预算，别设成无穷 |
| `maxNoProgressTicks` | `state.json.budget` | 3 轮，太大烧钱、太小误停 |
| `maxSubCallsPerLeaf` | `state.json.budget` | 8；外部调用多的任务可上调 |
| 子代理模型 | 运行时配置 | 用便宜档，主模型留给调度 |

## 3. 暂停 / 恢复 / 停止

- **暂停**：禁用定时任务（状态不丢）。
- **恢复**：重新启用，下一轮读盘接着跑。
- **彻底停**：删掉定时任务；想重来加 `--force` 重跑 `solo_init.py`（`artifacts/` 会保留）。

## 4. 故障对照表

| 现象 | 原因 | 处理 |
|---|---|---|
| 节点长期 `running` | 子代理崩了 / 回执没写 | 自动：>3×`maxLeafMinutes` 重试，超 `maxRetries` 置 `failed`。人工：看 `runs/<id>.json`、看子代理 transcript |
| 连续 N 轮零进展 | 目标不可达 / 卡凭证 | 停机上报；看 `DECISIONS.md` + 最后一个 `blocked` 节点 |
| 反复 `TOO_BIG` | 叶子判据太松 | 收紧任务书，或手动把该节点预拆一层 |
| 频繁限流 | 并发/间隔太激进 | 降 `maxLeavesPerTick`、加大间隔与 `staggerMs`、补 `models` 降级链 |
| `state.json` 写坏 | 并发写 / 手改 | 只让调度器单向写；从 `PROGRESS.md` + `runs/` 重建（回执含 outputs） |
| 报告引用路径不存在 | 产物没落盘 | `solo_validate.py` 会报错；补齐产物或修正报告 |

## 5. 四条不变量（改坏就失去全部优点）

1. 只有调度器写 `state.json`，且每轮只写一次。
2. 父会话永不读 `artifacts/` 正文。
3. 子代理永远隔离运行。
4. 任何「下一步要用的信息」必须在盘上，不能只在对话里。

## 6. 成本控制

- 隔离子代理 = 每轮新会话，上下文不累积 → 长跑的第 200 轮和第 1 轮一样便宜。
- 调度器只读 `state.json` + 回执，token 消耗恒定。
- 想彻底停烧钱：禁用定时任务（不动状态）。
