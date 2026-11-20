---
name: auto-edit-skill
description: "Run the original CapCut editing module for a user-requested editing-only task. For the full Douyin/Xiaohongshu topic-to-delivery workflow, use $douyin-automation, which routes to this module when appropriate."
metadata:
  display_name: 自动剪辑 Skill
---

# 自动剪辑 Skill

完整的热点、脚本、导演到剪辑流程统一从 `$douyin-automation` 进入。本 Skill 保留用户原有的剪映/CapCut 制作流程，作为总控调用的编辑模块；不要求用户切换窗口。需要独立执行剪辑流程时，仍可显式调用本 Skill。

把 GitHub Skill 的发现、审查、实测、录屏、脚本、剪映专业版剪辑、封面、质检和交付串成一个真实可复核的制作流程。视频必须原创，并以实际测试结果为依据；不得发布，除非用户明确授权。

先读取 [小西瓜风格规范](references/xigua-style.md)，再按 [制作流程](references/production-workflow.md) 执行；交付前逐项核对 [质量清单](references/quality-checklist.md)。

## 核心要求

- 先理解已有参考视频、拆解、提示词和项目素材，再决定选题与镜头。若参考材料找不到，说明缺少内容，不要假装看过。
- GitHub Skill 必须先做来源、维护情况、许可证、依赖和权限审查，再固定具体版本、安装并真实运行。明确区分“读过源码”“安装过”和“实际运行通过”。
- 先写基于实测的脚本和镜头表，再录制。关键画面必须来自真实操作，不能用概念图冒充结果。
- 正式剪辑必须使用用户要求的桌面版剪映/CapCut。仅使用当前界面确认可免费且授权范围适用的功能或素材；不使用会员内容、破解、未经确认授权的音乐，不用其他渲染器合成后冒充剪映成片。
- 若登录、权限、界面或导出限制阻止剪映完成，保留已有素材和工程，报告具体阻碍；不要虚报已导出，也不要擅自换软件。
- 封面、口播、脚本和演示均围绕本次实测原创制作。只借鉴叙事与视觉组织方法，不搬运博主作品、截图、音乐或原文。
- 质量检查只报告真实完成的项目。发布到抖音、小红书或其他平台必须等待用户明确授权。
