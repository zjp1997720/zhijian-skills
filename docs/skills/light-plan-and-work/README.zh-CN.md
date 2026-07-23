# Light Plan and Work

**用几步短计划完成边界清楚的任务，立即执行、按风险验证，只在后果和协作成本确实更高时升级到重流程。**

[English](./README.md) · [唯一源码](https://github.com/zjp1997720/zhijian-skills/tree/main/skills/light-plan-and-work)

## 安装

```bash
npx skills add zjp1997720/zhijian-skills \
  --skill light-plan-and-work --agent codex --global --copy --yes
```

使用 `$light-plan-and-work` 显式调用。它会选择任务编排方式，因此默认关闭自动触发。

## 运行要求

- Codex、Claude Code 等兼容 Agent Skills 的 Harness。
- 任务已经有明确结果和可控边界。
- 修改工作区时可以读取相关项目文件和项目规则。

## 它会做什么

- 锁定目标、交付物、边界和验收证据四项执行简报。
- 极简单任务直接执行；边界清楚的任务使用 3–7 步短计划。
- 展示计划后立即实施，不增加第二次批准门槛。
- 已有专用 Skill 能直接生产目标交付物时，优先调用专用 Skill。
- 方向、受众、概念和故事线尚未确定时，先路由到脑暴或需求发现。
- 涉及安全、破坏性操作、跨系统架构、迁移、多方协作和发布时升级到完整计划流程。
- 按风险做验证，最后交付结果、文件和证据。

## 工作方式

```text
读取上下文
  → 选择直接 / 轻计划 / 专用 Skill / 需求发现 / 重流程
  → 锁定执行简报
  → 制定 3–7 个可观察步骤
  → 连续执行
  → 按风险验证
  → 返回结果和证据
```

默认不创建计划文档。只有未来需要续接、外部交接、多方协作、长期设计决策，或用户明确要求时，才把计划写成文件。

## 使用示例

```text
用 $light-plan-and-work 把这些笔记整理成客户可审阅的培训简报，放到正确项目目录并校验最终文件。
```

```text
用 $light-plan-and-work 优化个人官网的一个模块，运行现有测试并返回改动文件。
```

```text
用 $light-plan-and-work 给这个 CLI 增加一个边界明确的小选项，做定向验证并保留无关改动。
```

## 安全边界与限制

- 手动触发可以避免编排型 Skill 抢占普通直接任务。
- 开放式方向选择属于脑暴或需求发现。
- 生产迁移、认证、支付、合规、破坏性动作、跨系统架构和协同发布使用重流程。
- 本 Skill 不削弱仓库规则、审批边界和外部动作授权。
- 一条命令通过，只能证明它覆盖的契约；未验证假设会保留在最终交付中。

## 开发与验证

```bash
python3 -m unittest discover -s skills/light-plan-and-work/tests -v
```

安装包还包含触发正例、负例、近邻样例，以及 baseline 与 Skill 输出对照评测。

## 许可证

[MIT](../../../LICENSE)
