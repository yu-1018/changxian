# LIMITS.md · 限流手册

不同 AI / provider 的限流维度、信号、回退策略都不一样。solo-loop 的策略是**不猜阈值**，统一按「降并发 → 冷却门 → 换模型」三层兜底。

## 1. 常见限流维度

| 维度 | 典型表现 | solo-loop 对策 |
|---|---|---|
| 每分钟请求数 (RPM) | 429 Too Many Requests | L1 并发=1 + L3 指数退避 |
| 每分钟 token 数 (TPM) | 429 / 请求被截断 | L6 子代理批量写盘、单会话调用上限 |
| 每日配额 | 403 / quota exceeded | L4 换模型；仍不行 → `blocked` 上报 |
| 并发上限 | 429 / 连接被拒 | R7 全局并发=1、单轮只派 1 个 |
| 免费档 / 试用额度 | 402 / insufficient_quota | L4 换模型；全挂 → `halted` 并说明 |

## 2. 识别限流信号（不限于 429）

- HTTP `429`、`503` 且带 `Retry-After`
- 响应体含 `rate_limit` / `too many requests` / `quota` / `overloaded`
- 报错文案含 `Please retry` / `slow down` / `capacity`

**关键**：限流**不是失败**。节点回 `ready`，`attempts` 不 +1，写退避冷却。

## 3. 退避公式

```
cooldownUntil = now + min(base × 2^count, maxBackoffMs) + rand(0, jitterMs)
base = 60s, maxBackoffMs = 30min, jitterMs = 30s
```

- 成功一次后 `count` 归零。
- `jitter` 必须有：多个任务/实例同时退避时避免同步重试再次撞墙。
- 尊重服务端 `Retry-After`：若它给出的时间更长，取更长者。

## 4. 多模型降级链

`state.json.models` 顺序即优先级：

```json
"models": ["主力-便宜快", "备用-贵但稳", "本地/自建"]
```

切换规则：当前模型连续 2 次限流或返回不可用 → 切下一个；切换次数写 `rateLimit.switches`。
全部不可用 → 进入冷却，等下一轮，**不要**在同一轮里死循环换模型。

## 5. 子代理内部的限流纪律（L6）

子代理最容易犯的错是「一个叶子任务里并发打几十个请求」。任务书必须写明：

1. 串行不并发，一次一个外部请求。
2. 批量写盘，减少往返。
3. 单会话外部调用 ≤ `maxSubCallsPerLeaf`（默认 8）。
4. 超限 → 回 `TOO_BIG` + 拆分建议，而不是硬打。

## 6. 定时任务层的抖动

定时唤醒不要都落在同一秒：定时任务加 `staggerMs ≥ 30s`；间隔建议 ≥ 5 分钟（叶子平均耗时短时可缩）。

## 7. 别把限流当停机

`noProgressStreak` 只在「无派发、无结清、且无任何 ready 可派」时 +1。
因限流而推迟派发**不算**零进展——否则一限流就误触停机（这是 v2 → v3 最重要的修正之一）。
