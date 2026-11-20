---
name: douyin-style-director
description: 独立分析参考视频风格、设计导演分镜或审查现有成片时使用；完整抖音/小红书短视频流程请从 $douyin-automation 进入，由总控调度本 Skill 的能力。
---

# 抖音视频风格学习与导演

完整选题到成片的请求从 `$douyin-automation` 统一入口进入。本 Skill 保留独立参考分析、导演方案与成片复核能力；作为子角色时按统一 Skill 的研究证据和剪辑交接契约交付，不要求用户切换窗口。

负责创意决策、证据记录、分镜和成片审查；实际剪切、合成、字幕、调色、混音和渲染交给当前可用的自动剪辑 Skill。先查该 Skill 的名称和输入要求，不预设接口。当前已知 `remotion-motion-graphics` 是可用实现之一，见 [交接规范](references/handoff.md)。

## 三种模式

- **学习参考**：读 [分析规范](references/analysis.md)，先核实链接和作品身份。只有拿到实际视频画面及声音，才能写“已观察”规则。把参考 MP4 放进 `references/videos/` 或用户指定目录；运行 `python3 scripts/director.py analyze <视频> --out <分析目录>`，亲自查看关键帧、片段并听音频，再用 `profile-init` 建档并填写证据。多个作品归纳共性，保留单片差异。
- **导演新片**：读 [交接规范](references/handoff.md) 和 [创作约束](references/production.md)。确认本期 Skill 的真实功能、实测结果、可用素材和授权；运行 `plan-init` 生成结构化方案，再补齐每镜头的内容与创意依据，运行 `validate-plan`。向自动剪辑 Skill 提供整个方案目录；没有素材的镜头标成待拍或待录，不伪造运行结果。
- **审查成片**：用 `analyze` 提取客观数据，再运行 `review <成片> <方案目录> --out <审查目录>`。逐段观看、听声，补充时间码、偏差、原因和可执行修改指令。自动检查只提供技术线索，不代替审美判断。

## 共通边界

- 每条风格规则写来源、时间码、画面/声音证据、使用条件、实现方法、禁用条件和可信度；无证据标 `待验证`。
- 区分观察到的剪法和未经后台数据验证的留存效果。不能编造点赞、BPM、原曲、镜头或效果。
- 参考风格优先；兼顾商业画面质量与 GitHub Skills 的真实清晰表达。学习决策逻辑，不重复套同一开头和花字。
- Flow 镜头只在有叙事必要时设计；未经授权不生成或消耗积分。AI 视觉隐喻不得冒充实际运行画面。
- 脚本需要 `ffmpeg`、`ffprobe`、Python 3；检测结果需人工复核。用法见 `python3 scripts/director.py --help`。
