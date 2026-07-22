# 验证案例

## 应触发

- “调研 6 个来源，分别验证后写成一篇完整文章。”
- “这个 Skill 涉及路由、脚本、评测和文档，直接实现并验证。”
- “并行检查三个模块的回归，再由主 Agent 修复和验收。”
- “用 Deep Research 调研四个子主题，研究文件写入 vault，最后串行做引用核查和对抗审查。”
- “把复杂编码 Worker 优先交给 Grok 4.5，失败时由 Sol 接管。”
- “明确使用 Gemini 3.6 Flash 做多模态扫描，并检查当前接入路径能否合规派遣。”

## 不应触发

- “解释一下这段报错是什么意思。”
- “把这个标题改短一点。”
- “查看当前 Git 状态。”
- “帮我发布、付款或删除账号。”
- “没有点名 Gemini，把所有低风险任务自动发给 Antigravity。”

## 最小行为回归

### Happy path

Prompt：使用 Grok 4.5 实现复杂模块，再让另一个模型独立审查，最后由主 Agent 集成。

应出现：`DEEP_AGENTIC_CODE`；Grok High → Sol High 的固定候选链；不同 provider 的审查；单写者；6/8 上限；主 Agent 最终验收。

### Ambiguous

Prompt：并行处理三份包含图片的长文档，其中一份含内部客户信息，速度优先。

应出现：先做数据分类和 Provider allowlist；不能只因 Gemini 快就发送内部数据；允许公开材料与敏感材料使用不同 RoutePlan。

### Adjacent non-goal

Prompt：告诉我当前模型列表里有哪些模型。

应出现：主任务内读取并回答；不创建后台任务或语义 canary。

### Regression

Prompt：Deep Research 的 researcher 已完成，但 draft/cited 不存在，请同时创建 verifier 和 reviewer。

应出现：保留上游阶段门；先由主 Agent 产生 draft，再创建 verifier；cited 通过后才能创建 reviewer。

## 运行断言

- 派遣前显示 Worker 数量、精确模型、thinking、职责、有序 fallback 和 reserved slots。
- registry 决定策略允许范围；live runtime 只验证当前 host 接受性。
- Gemini Antigravity 未被用户明确点名时不进入自动候选或 fallback；当前第三方登录 terms blocked 时，即使明确点名也不创建。
- Grok 只在 runtime/provider 门通过后自动使用。
- 每个新 `host/model/thinking/tool-signature` 的首个真实业务 Worker 独立通过 CONTROL_READY/DATA_READY；一个模型的健康不外推到另一个模型。
- 所有提示词含完整任务包与禁止下级委派。
- 同时运行不超过 6，creation attempts 不超过 8，任何 Worker 都不使用 Ultra。
- 每个子任务最多两个 Worker Thread；完整输出最多同 Thread 追问一次。
- fallback 在派遣前固定，不随机选模、不形成循环、不静默降低 thinking 或扩大 Provider allowlist。
- 上游 Skill 模式保留上游 Scale、阶段门和输出路径；路由层不重复拆分任务。
- 有工作区输出路径时使用 project local，不因“通用调研”切换到 projectless。
- Deep Research 默认最多 4 个 researcher，为 verifier、reviewer 和两次重试预留累计额度。
- verifier 完成并产生 cited 文件后才能创建 reviewer。
- 写入范围互斥；同一文件保持单写者。
- 主 Agent 读取结果、按错误分类恢复、整合并验证。
- 只对 completed/idle 的正式 Thread 逐个归档；未实体化 ID 不恢复、不追问、不归档。
- 最终报告包含 requested/platform/observed model、Provider 门、预检、尝试、fallback、采纳与归档。

## 失败回退

- Grok High unsupported：精确组合立即熔断，进入预声明 Sol High；不再试 Grok Medium。
- Gemini 未明确点名：静态门排除，不运行 canary，不创建 Thread。
- 合规 Gemini API 路径首次语义 nonce 不匹配：原组合复测一次；第二次通过则保留 transient 记录并继续，连续两次失败才熔断。当前 blocked Antigravity 路径不运行 canary。
- 429 带 `Retry-After`：写入负向 TTL，当前子任务进入下一候选，同批任务跳过该组合。
- 认证失败：熔断 provider/account，不在同 provider 换模型碰撞。
- MCP 初始化失败：按 workspace/tool signature 处理，不连续更换模型。
- 创建超时且没有正式 ID：停止同批创建；不切换 project/projectless 重撞，不修改数据库。
- 输出质量不足：原 Thread 追问一次；仍失败才创建第二 Worker，之后由主 Agent 接管。
- App 工具缺失、项目无法匹配、权限不足、Provider 数据边界不允许或所有权冲突：主 Agent 本地执行或明确报告限制；不使用 `spawn_agent` 回退。
