# 原生子 Agent 运行边界

本包内的 `agents/*.md` 是角色指令，主 Agent 会在协作工具可用时把对应指令交给真实子 Agent。主 Agent 负责阶段顺序与最终复核，用户始终从 `$douyin-automation` 进入。

Codex 当前任务环境提供真实协作工具，本次工作已实际启动运营、导演、剪辑三个子 Agent 完成并行只读审查。是否能在后续会话创建子 Agent，取决于会话运行时；角色 Markdown 不会自行开启权限。

对于 OpenAI Agents API，创建会话时需设置 `agent.multi_agent.enabled=true`；`max_concurrent_subagents` 可设为 3。OpenAI 官方文档将该值作为会话配置，技能的 `agents/openai.yaml` 是界面和调用元数据，不是多 Agent 开关。其他 Codex surface 应以当次会话实际暴露的协作工具为准，不猜测可用性。

如工具可用，通常按顺序调用运营 → 导演 → 剪辑，每个子 Agent 只写自己的阶段目录或返回结构化结果；需要来源核验/QA时，复核可与下一阶段并行。若工具不可用，就在同一对话中按三份角色指令逐步执行，不描述为并行 Agent。
