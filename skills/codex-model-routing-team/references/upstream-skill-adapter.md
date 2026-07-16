# 上游 Skill 适配协议

当 Deep Research、课程生产、PPT 或其他 Skill 已经定义工作流时，本 Skill 作为 Thread Orchestrator 执行。

## 决策边界

上游 Skill 拥有：

- 任务目标与 Scale
- 子任务划分
- 阶段顺序与依赖
- 产出路径与文件格式
- 业务验收与质量门

本 Skill 拥有：

- Worker `model` 与 `thinking`
- project / projectless 目标选择
- Thread 创建、实体化、读取、追问与归档
- 并发 6、累计 8、reserved slots 与升级次数
- 单写者和禁止下级派遣等安全边界

遇到冲突时，上游业务流程优先，路由安全上限保持强制。预算不足时收敛 Worker 数量并报告，禁止跳过上游验证阶段。

## 调用流程

1. 读取上游计划、任务账本、阶段门和输出路径。
2. 接受上游已经完成的 Scale，不重新拆分任务。
3. 计算当前阶段 Worker、后续阶段和重试的 reserved slots。
4. 输出派遣通知，列明当前 Worker 与保留额度。
5. 把上游任务转换成 `references/task-packet.md`，保留原始验收标准。
6. 有工作区输出时绑定匹配 project local。
7. 按 `references/thread-lifecycle.md` 创建、验证和读取 Thread。
8. 主 Agent 验证输出文件并更新上游账本。
9. 只有上游阶段完成且结果采纳后才归档。

每次 `create_thread` 成功后，立即把 `thread_id / role / model / thinking` 写入上游 run summary；完成验收和归档后补充 `status / output / archived`。`read_thread` 视图不保证返回模型字段，禁止依赖事后反查恢复路由信息。

## Deep Research 预设

```text
researcher_count + 1 verifier + 1 reviewer + retry_reserve <= 8
```

- researcher：默认 2-4 个，Luna X High；机械抽取可用 Luna High。
- verifier：1 个，Luna X High，在 draft 存在后创建。
- reviewer：1 个，Sol High，在 cited 存在并通过检查后创建。
- FATAL 复审：最多一次 Sol X High，使用 retry reserve。
- 所有任务绑定包含 `01_项目/调研` 的 vault project。
- 每个 researcher 写唯一的 T1/T2/T3/T4 文件。

## 状态复用

上游已经维护 plan 或 task ledger 时，在原账本增加以下字段：

```json
{
  "thread_id": null,
  "model": null,
  "thinking": null,
  "attempt": 0,
  "adopted": false,
  "archived": false
}
```

不要额外创建 `agent_team/state.json`。只有上游没有恢复机制且任务满足耐久模式条件时，才使用本 Skill 的独立状态目录。
