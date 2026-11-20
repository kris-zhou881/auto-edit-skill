# 原生子 Agent 运行边界

本包内的 `agents/*.md` 是角色指令，主 Agent 会在协作工具可用时把对应指令交给真实子 Agent。主 Agent 负责阶段顺序与最终复核，用户始终从 `$douyin-automation` 进入。

Codex 当前任务环境提供真实协作工具，本次工作已实际启动运营、导演、剪辑三个子 Agent 完成并行只读审查。是否能在后续会话创建子 Agent，取决于会话运行时；角色 Markdown 不会自行开启权限。

对于 OpenAI Agents API，多 Agent 需在创建会话时设置 `agent.multi_agent.enabled=true`。为减少同时占用的上下文和资源，默认按顺序调用，`max_concurrent_subagents=1`；只有用户明确要求并行时才提高并发。`agents/openai.yaml` 是展示和调用元数据，不是开关；其他 Codex surface 以当次会话实际提供的协作工具为准。

如工具可用，每次只调用一个子 Agent，按运营 → 导演 → 剪辑推进；交接只保留结论、证据 ID、文件路径、阻塞项和下一步。只加载当前阶段提示和相关参考，阶段结束后再调用下一个角色。若工具不可用，就在同一对话中轮换三份角色指令，不描述为并行 Agent。
