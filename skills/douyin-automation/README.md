# 抖音自动化skill

一个调用入口，默认由 Codex 自主完成热点/常青选题、真实实测、录屏、口播、Remotion 动态视频、封面和交付 QA；用户只负责手动发布。技术目录名 `douyin-automation`，Codex 展示名严格为“抖音自动化skill”。

## V2：不用参与制作，只手动发布

新项目默认选择 Remotion 做正式视频，不再强制进入桌面剪映。制作全过程请读 [无人值守生产流程](references/autonomous-production.md)。输入“用 $douyin-automation 做下一条视频”即可自动选题；如指定题材则直接开工。成片输出 视频-待人工发布.mp4、Remotion 可编辑工程、字幕、封面、发布文案和可复核报告。**Skill 永远不操作平台账号、不发布、不上传草稿。**

执行前运行 python3 scripts/doctor.py 检查环境。macOS 离线中文配音可运行 python3 scripts/synthesize_voice.py 口播.txt 项目目录/remotion/public/voice.wav；若未安装中文语音或声音生硬，须换有授权的可用配音方案并做音频 QA。实际视频工程运行 python3 scripts/render_autonomous.py init 项目目录，填入实录和配音后运行 python3 scripts/render_autonomous.py render 项目目录 --dry-run 做硬门禁预检，再运行正式 render。用户有意选择剪映时才启用旧版剪映分支。

## 安装

把本目录复制到 `~/.codex/skills/douyin-automation`，或在当前已安装该 Skill 的 Codex 中调用 `$douyin-automation`。不需要另开运营、导演和剪辑窗口。

Codex 会话允许原生子 Agent 时，主 Agent 按角色提示文件真实调用三个子 Agent；会话没有协作工具时，在当前窗口依次轮换三个角色。`agents/openai.yaml` 是 Skill 展示元数据，不会自行打开或启用子 Agent。Agents API 会话的多 Agent 开关由会话创建方设置。

## 使用

示例：

> 帮我研究最近适合抖音的 AI 工具话题，先核验热点和受众证据，再写脚本、做导演分镜，最后剪成 9:16 视频并交付 MP4 和可编辑工程。

如果你已给出选题、脚本、素材或指定剪映/Remotion，只做剩余阶段并沿用指定工具。热点指标需带来源和观察时间；没有平台数据时明确降级为候选题或常青题，不编造趋势。

## 验证

在本目录运行：

```bash
python3 -m unittest discover -s tests -v
python3 scripts/validate_project.py templates/project-manifest.json --root .
```

`project-manifest.json` 是模板，不含真实热点、素材或成片。`validate_project.py` 检查清单结构、证据引用、镜头时间线与交付状态；可加 `--check-files` 检查磁盘文件是否存在。`inspect_render.py` 用 ffprobe 检查实际视频的时长、画幅、帧率和音轨；人工观看和听声仍需单独完成。两个脚本都不会联网取数、验证平台数据真实性或渲染视频。

## 工具与权限边界

- 原导演 Skill、剪映流程和 Remotion 制作规范均随包保留；新包不自动安装第三方数据接口或外部服务。
- 抖音 scraper、小红书 MCP 是可选连接。登录、收费 API、验证码和平台互动必须有单独授权；本 Skill 不绕过风控、不自动发布。
- 素材/工程/封面/成片默认保存到 `~/Desktop/视频/<项目名>`，用户指定位置时按指定位置保存。
- 完整人工观看和听声后才能标记 QA 通过；脚本检查只表示结构或技术项已检查。

## 文件

- `SKILL.md`：唯一调用入口与总控流程。
- `agents/`：三份专业角色提示；子 Agent 由运行时调用，不是三个独立窗口。
- `modules/`：随包保留原导演与 Remotion Skill 的指南、参考文件、脚本和主题组件，不作为额外的用户入口。
- `templates/project-manifest.json`：每期项目与证据清单。
- `references/`：导演接口、研究/剪辑交接、原生多 Agent 边界、上游来源与用户已有剪辑资料。
- `scripts/validate_project.py`、`scripts/inspect_render.py`、`tests/`：项目清单与渲染文件技术检查及测试。

## 创意质量升级

抖音项目统一按 [留存优先规则](references/douyin-retention.md) 执行：首帧钩子、5 秒内兑现、镜头尽量不超 3 秒、问句收尾和配套封面标题。GitHub 高星 AI Skill 动画另按 [动画制作流程](references/github-skill-motion.md) 执行，随包提供 Remotion 可渲染工程。

新项目默认 Remotion 最终导出；用户显式要求剪映才使用原桌面剪映专业版。先三种钩子选一，口语化分段脚本，再逐镜头声画设计和免费资源实查，最终六项实际看听验收；任一失败改稿/重剪。按 `references/creative-quality.md` 使用 `validate_project.py --stage script|director|edit|final`（每次选择一个阶段），最终加 `--check-files`；已渲染/交付状态始终强制较高门槛。旧项目不重建，补齐新增记录后再完成制作。代码只验证记录与文件，不负责登录剪映、试听素材或自动判断自然度。
