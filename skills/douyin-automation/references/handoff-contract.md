# 四角色项目交接契约

`templates/project-manifest.json` 是每期项目记录。Agent 可以使用其他中间格式，但每次交接前须把可验证状态写回项目清单，不得用空字段掩盖缺口。

## 阶段交接

| 交接 | 必须包含 |
|---|---|
| 主控 → 运营 | 平台、研究时段、目标人群、题材限制、用户已给素材/脚本及允许的数据源 |
| 运营 → 主控/导演 | 证据来源与观察时间、指标原值、样本范围、受众依据及状态、候选题、选题判断、脚本与证据缺口 |
| 主控 → 导演 | 选定主题、可验证主张及证据 ID、平台/时长/画幅、风格要求、已核验素材与授权、缺口 |
| 导演 → 剪辑 | 原导演 Skill 七份 JSON、真实素材路径与许可、字幕/口播、声音/转场、画幅帧率、需保持的创意和 QA 项 |
| 剪辑 → 主控 | 实际使用的剪辑工具/版本、输出路径、MP4 与可编辑工程、素材/许可清单、技术检查结果、人工观看时间及遗留问题 |

## 研究字段

`research.status` 取 `verified`、`limited`、`unavailable` 或 `not_requested`。`verified` 至少需要一条目标平台来源，以及至少一项带原始值/单位/时间的可见流量或互动指标。`limited` 与 `unavailable` 必须给出限制；新闻来源不能伪装成平台热度。

每个 source 有唯一 `source_id`、平台、标题、URL、可选发布时间、带时区的 `observed_at`、受众依据状态和原始指标。所有脚本 claims 标记 `verified`、`inferred` 或 `unverified`；`verified` 必须引用存在的 source ID。受众标记 `observed`、`inferred` 或 `unavailable`，并按证据解释。

## 分镜和剪辑字段

镜头时间以秒计，按序首尾相接，不得负值或倒序。素材状态 `ready`、`missing`、`pending`；`ready` 应有本地路径。`missing`/`pending` 允许方案验证通过，但禁止标记为已渲染。

抖音竖屏视频默认 9:16，封面同时列横版 4:3（1440×1080）和竖版 3:4（1080×1440）。用户明确指定其他平台尺寸或横屏作品时记录实际目标并按实际尺寸检查。

`editing.status` 取 `not_started`、`blocked`、`rendered`、`qa_pass`。`rendered` 要有 MP4 和可编辑工程路径并且所有镜头素材就绪；`qa_pass` 还需通过技术检查与人工看/听记录。项目清单验证只检查结构和所声明状态；`--check-files` 才查真实文件存在。它不打开视频，也不能证明素材权利或数据真实。

`delivery.published` 默认 `false`。只有用户对具体发布动作明确授权后才可以更新为 `true`，并将 `publish_authorized` 记为 `true`；Skill 不自动发布。
