# 自动剪辑 Skill

## 统一入口

完整的抖音/小红书流程从 `skills/douyin-automation/` 进入，Codex 展示名为「抖音自动化skill」。它统一调度热点运营、导演与自动剪辑角色，不需要用户开多个窗口。

在 Codex 中将 `skills/douyin-automation` 目录复制为 `~/.codex/skills/douyin-automation`，然后调用 `$douyin-automation`。仓库根目录的 `$auto-edit-skill` 保留为原有剪映/CapCut 兼容编辑模块，不会作为自动入口与主 Skill 争抢调用。

## 仓库根目录的原剪辑模块

根目录的 `SKILL.md`、`references/` 与 `agents/openai.yaml` 继续保留原有剪映制作规范；完整热点到成片任务由新入口统一调度。

## 旧模块内容

让 Codex 按照「西瓜同学🍉」的可验证风格规律，完成 GitHub Skill 选题、审查、实测、真实录屏、剪映专业版剪辑、封面和交付质检。

使用前确保本机有剪映专业版；此模块不会用其他视频渲染器替代最终剪辑。

原有参考资料继续保留：

- `SKILL.md`：入口和必须遵守的边界。
- `references/xigua-style.md`：基于 7 条已观看样本提炼的风格规范，附证据范围和未知项。
- `references/production-workflow.md`：从 GitHub Skill 发现到剪映工程和交付的制作流程。
- `references/quality-checklist.md`：风格、真实性、授权与技术检查清单。

视频只能在用户验收后由用户自行发布；不得虚报实测、授权、剪映导出或封面分辨率。
