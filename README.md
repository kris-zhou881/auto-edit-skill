# 自动剪辑与抖音短视频自动化 Skill

## 统一入口

完整的抖音/小红书短视频制作流程统一从 `skills/douyin-automation/` 进入（Codex/Antigravity 展示名为「抖音自动化skill」）。它统一调度热点运营、导演分镜与自动剪辑角色，不需要用户开多个窗口。

- **Codex 安装**：将 `skills/douyin-automation` 目录复制或链接到 `~/.codex/skills/douyin-automation`，然后调用 `$douyin-automation`。
- **Antigravity 安装**：将 `skills/douyin-automation` 复制或链接到全局技能目录 `~/.gemini/config/skills/douyin-automation`，Agent 将自动发现并调用该 Skill。
- 仓库根目录的 `$auto-edit-skill` 保留为原有剪映/CapCut 兼容编辑模块，不会作为自动入口与主 Skill 争抢调用。

## 最新特性与更新（2026-11-22）

1. **抖音留存优先剪辑规则 (`references/douyin-retention.md`)**：
   - **首帧即钩子**：第 1 帧直接显示兑现钩子的真实画面，严禁片头、标题卡或缓慢铺垫。
   - **0–2 秒抓人**：明确核心收益或认知反差，2–5 秒内迅速兑现关键信息。
   - **快节奏紧凑剪辑**：单镜头尽量不超过 3 秒，真实操作/代码镜头有充分理由可适当放宽并保持视觉进展；无拖沓空镜或冗余过渡。
   - **克制高对比大字字幕**：重点词统一着色强调，不堆砌繁杂花字与遮挡特效。
   - **问句结尾**：视频结尾采用引发讨论的互动问句，提升完播率与互动留存。
   - **配套封面标题**：导出时单独交付一条吻合首帧钩子的专属封面标题文案。

2. **Remotion 动态技术演示与运镜模版 (`templates/remotion/`)**：
   - 新增 Remotion 代码动效渲染套件与分镜时间轴驱动脚本（`animation.jsx`, `timeline.mjs`, `check-timeline.mjs`）。
   - GitHub 高星 AI Skill 视频优先使用 Remotion 生成平滑运镜、逐行代码高亮和音画预览，再送入剪映进行分轨总装。

3. **真实素材与代码动效剪法 (`references/evidence-led-editing.md`)**：
   - 支持真实照片（`photo` 类型）及严格的 `source_identity` / `author` / `rights` 来源追溯，防止同一照片重复使用。
   - 真实素材独占成片时长严格要求 > 50%。

4. **自动化质检与环境自检**：
   - `scripts/inspect_technical.mjs`：升级逐秒质检，新增照片去重检测与来源权属核验。
   - `scripts/creative_quality.py`：新增首帧钩子真实画面就绪校验（`hook_visible` 门禁）。
   - `scripts/doctor.py`：一键自检 Python、ffmpeg、ffprobe、Node.js、Swift 及模版依赖。

## 目录结构

- `skills/douyin-automation/`：核心完整 Skill（含调度、分镜、剪辑、动效与自动化脚本）
  - `SKILL.md`：总控入口与调度规范
  - `agents/`：热点运营、导演、自动剪辑角色定义
  - `modules/`：导演分镜模块、Remotion 动效模块
  - `references/`：抖音留存规则、真实素材剪法、技术讲解流程、动效指南等
  - `scripts/`：自动剪辑、质检抽帧、创意门禁、环境自检脚本
  - `templates/`：清单模版、分镜模版、Remotion 项目模版
  - `tests/`：自动化测试套件
- 根目录 `SKILL.md`、`references/` 与 `agents/openai.yaml` 继续保留原有剪映制作规范。

视频只能在用户验收后由用户自行发布；不得虚报实测、授权、剪映导出或封面分辨率。
