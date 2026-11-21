---
name: remotion-motion-graphics
description: Implement or render a Remotion project when the user specifically requests Remotion, React motion graphics, animated titles, or a Remotion project edit. For end-to-end Douyin/Xiaohongshu planning and production, use $douyin-automation, which may route implementation here. Read this skill before writing Remotion code.
---

# Remotion Motion Graphics

For complete short-video work, start from `$douyin-automation`; this Skill is its Remotion implementation module and can still be called directly for standalone Remotion work.

Remotion renders React components frame-by-frame into video. Code quality is not the
bottleneck — **motion design craft is**. Untrained generation produces linear easing,
opacity-only fades, simultaneous entrances, flat colors, and no texture. That is the
"generic AI video" look. This skill exists to prevent it.

## Non-negotiable rules (apply to EVERY composition)

1. **Avoid raw linear motion progress.** Drive motion progress with an easing curve or
   `spring()`; a linear value mapping from an already-eased progress value is fine.
   Clamp values at their intended bounds. Use `linearTiming()` only when a transition
   deliberately needs uniform travel.
2. **Entrances animate 2–3 properties together** (opacity + translateY + scale).
   A lone fade is forbidden.
3. **Stagger everything.** Lists, words, rays, cards: 3–6 frame offsets. Nothing
   enters simultaneously.
4. **Exits exist and are faster than entrances** (~10 frames vs ~20).
5. **Use the five-layer stack for designed motion-graphics scenes**, bottom to top:
   background → assets → graphics/type → color grade → optional grain/vignette. A
   real screen recording may remain clear and stable; do not add layers that reduce UI
   readability.
6. **Decorative still images can use Ken Burns.** Keep screenshots, product UI, and
   evidence frames stable unless a purposeful crop/zoom is needed. Every video asset
   uses `<OffthreadVideo>`, never `<Video>`.
7. **Decorative idle elements may breathe** when it helps the scene. Do not animate
   real interface content or captions in a way that makes them harder to read.
8. **All timing derives from `fps`** via `useVideoConfig()`. No magic frame numbers.
9. **One theme object** at the top of the project (colors, easings, spring presets,
   fonts). Never inline a hex color or easing in a component.
10. **Render, extract frames, LOOK at them, fix, re-render.** Never deliver an
    unverified render. This loop is mandatory — see Verification below.

## Workflow

### 默认保存位置

每次做视频，默认把可复用素材和交付文件统一保存到 `~/Desktop/视频`（或用户指定/项目清单配置的输出目录）。包括原始素材的项目副本、录屏、图片和封面、配音和音乐、字幕、可编辑工程及导出的成片。可以按项目建子文件夹。工具先把文件生成到其他位置时，交付前复制到这个目录；剪映导出时优先选择这个目录。临时渲染文件可继续放在工作目录。用户为本次任务指定其他位置时，按本次指定的位置保存。

### 抖音封面比例

横封面默认用 4:3（1440×1080），竖封面默认用 3:4（1080×1440）。按交付尺寸检查标题和人物主体的裁剪。成片比例按视频任务要求设置。

### 抖音封面人物与风格

- **唯一固定的是人物身份。** 主角统一使用第一张参考里的同一位中国男大学生：约 20 岁，保留可辨认的脸、黑色自然卷发和细黑框眼镜。横竖两版和后续选题都要认得出是同一个人。
- **其余元素都可以换，封面默认要夸张、吸睛。** 场景、光线、色调、服装、道具、动作、表情、视线、镜头、构图、字体和标题按选题大胆重做。允许荒诞的场景和反差，用主角的动作把视线引向选题主体。例如讲小店利润，可以让主角站在悬崖边指向孤峰上的小卖部。
- **标题缩小到手机列表也要一眼看清。** 把最抓人的关键词做大做粗，按画面需要用撞色、粗描边或夸张排版。给脸、手势和故事主体留空间。夸张用在画面创意和标题处理，实测结果、金额和功能必须与内容一致。
- 优先使用用户第一张原图锁定人物。原图未随任务提供时，使用桌面「视频/封面角色参考/卷发眼镜男生.png」。分别验收横版 4:3 和竖版 3:4，再存到桌面「视频」对应项目。

### Step 1 — Scope
Determine: duration, fps (30 default; 60 only for heavy fast motion), dimensions
(1080×1920 Reels/Shorts, 1920×1080 landscape), what assets exist (images, footage,
audio, logos), and whether this is a new composition or an edit to an existing project.
If editing an existing project: read `src/` fully first, find the theme (or create one),
and refactor violations of the rules above before adding features.

### Step 2 — Setup
New project:
```bash
npm install remotion @remotion/cli react react-dom
# optional: @remotion/transitions @remotion/motion-blur @remotion/google-fonts
```
Copy `assets/theme.ts` from this skill into `src/theme.ts` and adjust the palette to
the user's brand. Structure: `src/index.ts` (registerRoot) → `src/Root.tsx`
(Composition, duration/fps/size) → `src/scenes/*.tsx` → `src/components/*.tsx`.
User assets go in `public/`, loaded via `staticFile()`.

### Step 3 — Build
Read `references/motion-patterns.md` for the reusable component implementations
(BgMesh, Grade, Grain, Vignette, KenBurns, WordReveal, Stagger, Counter, Spark,
transitions, parallax). Compose scenes from those patterns. For pacing, rhythm,
typography, color palettes, and sound design rules, read
`references/design-rules.md`.

Scene rhythm: HIT → hold (15–20 still frames) → build → HIT. Something must move
in the first 15 frames. Never >90 frames without a new visual element.

### Step 4 — Render
```bash
npx remotion render src/index.ts <CompId> out/video.mp4 --codec h264 --crf 17
```
Remotion needs a Chromium binary. If its auto-download fails (sandboxes, offline CI),
find one and pass it explicitly:
```bash
which chromium chromium-browser google-chrome 2>/dev/null
ls /opt/pw-browsers 2>/dev/null   # Playwright installs live here
npx remotion render ... --browser-executable=<path>
```
If full Chrome errors with "Old Headless mode has been removed", use a
`headless_shell` binary instead (Playwright ships one as
`chromium_headless_shell-*/chrome-linux/headless_shell`).

### Step 5 — VERIFY (mandatory, never skip)
Use `ffprobe` to read the actual duration and frame rate, choose valid sample times
near the beginning, middle, end, and any complex effect, then extract those frames
with `ffmpeg`. Record the timestamps and inspect them; never use a guessed frame
count or placeholder such as `N-10` as though it were a literal frame number.
Look for, and fix, in order of frequency:
- **Spacing bugs**: `gap`/`margin` in `em` resolves against the PARENT font-size
  (often 16px), not the text size — use px values in flex containers around big type.
- Text overflowing or touching frame edges (keep critical content in middle 75%
  vertically for 9:16 — platform UI covers top/bottom).
- Elements visible before their entrance or after their exit (missing clamp).
- Color/contrast failures: hero color on >1 element per frame, dim text unreadable
  over the grade.
- Layer order mistakes (grain/vignette must be on top, grade above content).
Fix → re-render → re-extract → re-inspect. Only deliver after a clean pass.
Then run the final checklist at the bottom of `references/design-rules.md`.

### Editing the user's existing footage
To enhance an existing mp4 (captions, grade, intro/outro) rather than build from
scratch: put the file in `public/`, render it as the asset layer with
`<OffthreadVideo src={staticFile("clip.mp4")} />`, set composition duration from the
clip length, and stack graphics/grade/grain above it. Get the clip's duration and fps
with `ffprobe` before setting up the composition. For word-synced captions over
speech, see the captions section of `references/motion-patterns.md`.

## Reference files
- `references/motion-patterns.md` — copy-paste component library: backgrounds,
  grade/grain/vignette, Ken Burns, text reveals, counters, transitions, parallax,
  audio sync, captions. Read before writing components.
- `references/design-rules.md` — palettes, typography rules, scene architecture,
  sound design, pre-delivery checklist. Read before designing scenes and before
  final delivery.
- `assets/theme.ts` — the theme template to copy into every project.

## Common failure modes to actively avoid
- Generating one giant component instead of themed, reusable pieces.
- `durationInFrames` mismatch between Composition and scene content (dead air).
- Forgetting `--overwrite` on re-renders, then inspecting the stale file.
- Fonts: never rely on system defaults for hero text; load a display font via
  `@remotion/google-fonts` or `@font-face` + `staticFile`.
- Trying to "describe" the result to the user instead of rendering and verifying it.
