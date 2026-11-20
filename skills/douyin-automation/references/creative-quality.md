# 创意质量执行契约

只研究选题时交证据/候选；开始视频制作时执行以下门槛，阶段未通过不能继续。阶段检查不会生成画面、调用剪映或判断审美，不得把字段齐全称作创意实测通过。

## 四个门槛

使用 `python3 scripts/validate_project.py project-manifest.json --stage <阶段>`；最终加 `--check-files`。

- script：script.hook_candidates 至少三条不同 kind/text，每条 hook_id、visual_proof、proof_status、appeal_reason；selected_hook_id、selection_reason；hook 文本须与选中项相同。script.beats 至少两段，各含 text、emotion、pause_after_ms，情绪至少两种且有正值停顿。候选阶段允许 pending，剪辑前选中 proof_status 必须 ready。文字自然度仍由实际试读/试听验收。
- director：继承 script；director.shots 中每镜头含 visual_source、caption、caption_style、motion、transition、music、sfx、voice_emotion。首镜头从0秒开始、opening_result=true，必须写真实结果来源；禁止标题卡冒充。不用某资源时写明原因，不硬塞音效。
- edit：继承 director；选中钩子已就绪；editing.engine 默认 jianying_desktop。其他引擎必须有 engine_override.engine/reason/user_instruction（记录真实用户要求，不得自填授权）。preflight.status=passed、有 checked_at、app_version、operation_evidence；resources 至少覆盖 voice/caption/transition/music/sfx，分别记录 name、free=true、license_status=verified、license_scope、evidence、checked_at。资源证据来自当期实际界面与许可，不把历史免费状态当现状。blocked 时写 blocker/recovery_action，返回错误并报告，不继续渲染。
- final：继承 edit；必须 editing.status=qa_pass；creative_review.status=passed，记录 reviewer、reviewed_at、render_path，与当前导出一致，并记录 render_sha256（成片 SHA256）；--check-files 读取文件核对，防止同名重导出沿用旧报告。checks 的 opening/rhythm/captions/voice/music/transitions 六项均 passed、evidence（时间码+观察）、issues=[]。同时仍需 technical_qa、human_review、MP4 和可编辑工程。--check-files 检查路径存在，不判断画面真伪/软件来源。

## 验收与恢复

主 Agent 实际从头看听本次导出，记录第一眼看见什么、何时产生问题/反差、节奏有无拖沓、字幕是否遮挡/单调、配音停顿重音是否自然、音乐是否抢人声、转场是否服务信息。花字/转场/声音重在合适，禁止机械堆叠。观察无法完成时保留 not_run，不能勾 passed。

任一项 failed，editing.status 不得 qa_pass，delivery 不得 ready；写 rework_log（issue、action、status=open/resolved），主控把脚本/镜头问题交运营或导演，执行问题交剪辑。完成后重新导出、看听和验收；保留旧版本记录。软件受阻写 blocked；若用户明确改工具，保留原因与实际引擎，不能伪装剪映成片。

## 规则冲突的处理

- 本账号最新要求优先：默认剪映，不再优先沿用 Remotion；其他引擎仅用户明确选择。
- 旧白色字幕样本是历史观察，不是默认黑底白字模板。
- 字号、安全区、米色配色、真实画面比例、动效频率沿用竖屏规范；小幅有意义的变化满足节奏，不晃动真实网页影响阅读。
- 结尾≥4秒指构图/文案保持，可有轻微动效；内容真实性和许可始终优先。
