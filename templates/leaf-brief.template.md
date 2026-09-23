# 叶子任务书 · 节点 {{id}}「{{title}}」

## 背景（自包含，读完即可开工，不要问任何人）
{{context}}

## 交付
{{deliverable}}

## 输入（只读这些）
{{inputs}}

## 输出（必须写盘）
- 产物：`{{artifacts}}`
- 回执：`{{LOOP_ROOT}}/runs/{{id}}.json`

## 验收（不满足即未完成）
{{acceptance}}

## 限流纪律（硬性）
- **串行不并发**：一次只发一个外部请求，不要 fan-out。
- 收到 429 / 限流 → 指数退避重试（带抖动，尊重 `Retry-After`），最多 3 次；仍失败 → 回执 `BLOCKED`，`next` 写清限流。
- 批量写盘；本会话外部调用 ≤ {{maxSubCallsPerLeaf}} 次，超了回 `TOO_BIG` 并给拆分建议。

## 回执格式（JSON，写完即结束）
```json
{"id":"{{id}}","status":"DONE","summary":"≤120字结论","outputs":["相对路径"],"evidence":"1-3条可核验证据","next":""}
```
`status`：`DONE` / `BLOCKED`（缺凭证或缺前置，`next` 写清缺什么）/ `TOO_BIG`（超单会话能力，`next` 给拆分建议）。

## 规则
- 必须**单次会话内**完成；不向任何人提问；缺凭证 → `BLOCKED`。
- 只写上面两个路径，不动其他文件。
- 时限 {{maxLeafMinutes}} 分钟；最终只回一段 ≤120 字结论，**不要复述产物内容**。
