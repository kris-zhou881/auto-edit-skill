# 借鉴来源与边界

以下仓库只借鉴工作方法，未把它们作为本 Skill 的安装依赖，也未打包其代码、字幕或媒体。需要使用时必须重新核对来源当前状态、许可证、权限和依赖。

- [self-media-content-workflow](https://github.com/yanhua1010/self-media-content-workflow/tree/1cdc2465c853d35ce2cfcf6826c5de872fa484cf)：按平台/时间/受众定义样本，分别记录事实、重复模式与推断。其跨平台脚本会用到 `AISA_API_KEY`；确认服务条款与费用并获授权前，改用有限公开来源。
- [viral-topic-picking](https://github.com/liush2yuxjtu/douyin-video-skill/tree/5c6414f3e74fcb52ab361e5ca9d0a89c7e6cd613/skills/viral-topic-picking)：借鉴受众关联、现实利益、认知反差、理解成本等选题判断维度，不复制字幕或未经证实的算法结论。
- [video-shotcraft](https://github.com/Vincentwei1021/video-shotcraft/tree/075b548c2405a07b77129eb448b0b504fc60dea3)：镜头设计思路参考；优先服从用户实际风格、素材可用性和真实网页可读性。
- [vidmoat/skills](https://github.com/vidmoat/skills/tree/ec2c2a944a2d4524d4b3affc6af315511946d6b5)：可参考其工具无关的剪辑、字幕和声音设计指导；不把任何手法当作固定模板。
- [why20261/douyin-data-scraper](https://github.com/why20261/douyin-data-scraper/tree/e8a0e6abc719a9950d119bd04813827ae061c022)：可选数据适配器候选，依赖第三方 `GUAIKEI_API_TOKEN`，请求会发往 guaikei.com 并受套餐/余额限制；不是官方或默认免费接口。未获授权不安装/调用，授权错误时停止。
- [xpzouying/xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp/tree/bb6fa2e208719ee634fec37881be29d3aa4699b3)：可选小红书读取接口，需要登录；仓库同时包含发布、评论和点赞收藏能力。本 Skill 只考虑已授权只读数据，不自动互动。
- [remotion-dev/skills](https://github.com/remotion-dev/skills)：未新增安装；本机已经有 Remotion Skill，本项目优先沿用现有工程和指导。
- [renezander030/capcut-cli](https://github.com/renezander030/capcut-cli)：未安装；当前已有用户自己的剪映制作流程，先沿用其真实桌面工程与授权边界。
- [OpenAI Multi-agent 文档](https://developers.openai.com/api/docs/guides/agents-api/multi-agent)：会话级能力，需创建会话时启用；不是 Skill 的 `agents/openai.yaml` 字段。
- 已存在的本机 `douyin-style-director`、`remotion-motion-graphics` 与用户 GitHub `auto-edit-skill` 是本项目优先沿用的既有资产；不得因为参考仓库存在就重复安装替换。

引用的具体提交、许可或接口说明会漂移；仓库主页只作为入口，不代表当前可访问、免费或可用。
