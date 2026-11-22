# 导演与剪辑交接

运行 `plan-init <方案目录>` 生成七份 JSON：`director_brief`、`shot_plan`、`timeline`、`typography_plan`、`transition_plan`、`audio_plan`、`quality_checklist`。每个镜头必须有 `start/end`、`asset.path/type`、`source_in/source_out`、`crop`、`grade`、`text_events`、`transition_out`、`sfx_events`、`music_beat_reference`、`voiceover`、`narrative_goal`。时间单位为秒；区间为左闭右开；路径用绝对路径或相对方案目录的路径。待拍素材用 `status: missing`，不能渲染时当作已有。初始化只拒绝覆盖现有目标 JSON，不删除其他项目文件。

导演应填写每期选题的真实功能和实测证据，设计首帧到 2 秒的钩子、2–5 秒的核心兑现和中段新信息；单镜头尽量不超过 3 秒，末句为相关问句，再给出有因果关系的镜头。`timeline.json` 是执行基准；其他文件提供创意说明和详细事件。`validate-plan` 检查时间连续性、素材入出点、必填字段和目标总时长，不检查字幕/音效/转场事件的时长。通过验证不代表内容真实、素材已授权或画面合格。

当前扫描到 `~/.codex/skills/cat-video-editor/SKILL.md` 的注册名为 `remotion-motion-graphics`。它没有固定 JSON 输入 API，以 Remotion 项目素材、场景组件和时间线渲染为主。因此兼容层是 `export-remotion <方案目录> --out <文件>`：导出按 fps 计算的场景帧区间和素材映射，交给该 Skill 构建组件；动态花字、转场、混音与调色仍由剪辑 Skill 按导演方案实施。输出会明确列出缺失素材；导出成功不代表素材齐全、Remotion 工程已建或成片已渲染。调用前重读其最新 SKILL.md，若已换剪辑 Skill，按实际接口映射，不让执行方重定整体风格。

示例调用：

- 学习：“用 `$douyin-style-director` 分析 `references/videos/参考1.mp4`，更新风格档案，所有结论附时间码。”
- 导演：“用 `$douyin-style-director` 为这个 GitHub Skill 的真实演示设计 30 秒竖屏方案，验证后交给 `remotion-motion-graphics` 渲染。”
- 审查：“用 `$douyin-style-director` 对成片和导演方案逐段审查，输出带时间码的修改清单。”
