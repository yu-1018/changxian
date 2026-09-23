# solo-loop

> 把一个长期目标变成**无人值守、可断点续跑、永不上下文爆炸、抗限流**的长循环任务。

`Claude Code` / `OpenClaw` / 任何支持 AgentSkill 的运行时都能装载。

## 为什么值得装

1. **不炸上下文** —— 调度器只读 `state.json` 和一个回执文件；子任务在隔离会话里干活，只回 ≤120 字结论、产物写盘。父会话永远是「当前这一轮」大小，跑 200 轮也不膨胀。
2. **不丢进度** —— 所有状态落盘（任务树 / 游标 / 预算 / 限流），进程崩溃、机器重启、网关重启都不影响，下一轮读盘接着跑。
3. **不烧钱空转** —— 三条显式停机线：任务全完成 / 预算（轮次）耗尽 / 连续 N 轮零进展。命中即写终报告并**删掉自己的定时任务**。
4. **不怕限流** —— 降并发（并发=1 + 抖动）、冷却门（限流期间只对账不计零进展）、多模型降级（主挂切备）三层兜底，不绑定任何一家 API。
5. **不过度规划** —— 惰性展开：只在分支轮到执行时才拆下一层，避免一次性拍平整棵树导致的返工。
6. **零依赖** —— 三个纯标准库 Python 脚本，不需要服务器、不需要装包、不需要付费服务。

## 安装

```bash
git clone https://github.com/yu-1018/solo-loop.git
cp -r solo-loop ~/.claude/skills/        # 或你的运行时 skills 目录
```

## 使用

```bash
python scripts/solo_init.py --root ./my-loop --goal "要什么 + 成功判据"
```

然后告诉你的 agent：「读 `my-loop/INSTRUCTION.md`，按 SKILL.md 建定时任务并开始跑」。

进度与校验：

```bash
python scripts/solo_status.py   --root ./my-loop     # 看进度
python scripts/solo_validate.py --root ./my-loop     # 校验状态 + 报告自检
```

## 结构

```
SKILL.md            驱动器完整规范（装载入口）
scripts/            init / status / validate
templates/          state、任务书、定时任务 payload、进度表
references/         LIMITS.md 限流手册、RUNBOOK.md 运维与故障
examples/           示例目标
```

## 兼容性

- Python ≥ 3.8，纯标准库。
- Windows / macOS / Linux 均可。
- 有定时器就自动化，没有就手动「跑一轮」，协议完全一致。

## License

MIT
