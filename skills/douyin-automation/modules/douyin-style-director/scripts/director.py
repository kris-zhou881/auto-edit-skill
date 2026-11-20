#!/usr/bin/env python3
"""Evidence-first video analysis and editor handoff. Requires ffmpeg/ffprobe."""
import argparse
import json
import re
import shutil
import statistics
import subprocess
from pathlib import Path


def run(cmd, check=True):
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def probe(video):
    result = run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)])
    return json.loads(result.stdout)


def video_duration(info):
    return float(info["format"]["duration"])


def shot_boundaries(video, duration, threshold):
    result = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", f"select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"], check=False)
    times = [float(x) for x in re.findall(r"pts_time:([0-9.]+)", result.stderr)]
    return [0.0] + sorted(set(round(t, 3) for t in times if 0 < t < duration)) + [duration]


def analyze(video, out, threshold=0.32):
    if not video.is_file():
        raise ValueError(f"视频不存在: {video}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("需要 ffmpeg 和 ffprobe")
    out.mkdir(parents=True, exist_ok=True)
    info = probe(video)
    duration = video_duration(info)
    bounds = shot_boundaries(video, duration, threshold)
    shots = [{"id": i + 1, "start": round(a, 3), "end": round(b, 3), "duration": round(b - a, 3), "detection": "automatic_scene_candidate"} for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]
    put(out / "probe.json", info)
    put(out / "shots.json", {"source": str(video.resolve()), "threshold": threshold, "note": "自动场景候选，须观看原片复核；不等于真实剪辑点", "shots": shots, "stats": {"count": len(shots), "mean_seconds": round(statistics.mean(s["duration"] for s in shots), 3), "median_seconds": round(statistics.median(s["duration"] for s in shots), 3)}})
    frames = out / "keyframes"
    frames.mkdir(exist_ok=True)
    for i, s in enumerate(shots[:25], 1):
        t = (s["start"] + s["end"]) / 2
        run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video), "-frames:v", "1", "-vf", "scale=360:-2", str(frames / f"frame_{i:03}.jpg")])
    if list(frames.glob("frame_*.jpg")):
        run(["ffmpeg", "-v", "error", "-y", "-framerate", "1", "-i", str(frames / "frame_%03d.jpg"), "-vf", "tile=5x5:nb_frames=25:padding=4:margin=4", "-frames:v", "1", str(out / "contact_sheet.jpg")], check=False)
    if any(s.get("codec_type") == "audio" for s in info["streams"]):
        run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-filter_complex", "aformat=channel_layouts=mono,showwavespic=s=1200x240:colors=white", "-frames:v", "1", str(out / "waveform.png")], check=False)
    lines = [f"# 自动分析时间线：{video.name}", "", "场景切点为候选；实际镜头、转场、叙事和声音需人工复核。", "", "| 镜头 | 起点 | 终点 | 时长 | 关键帧 |", "|---|---:|---:|---:|---|"]
    for s in shots:
        key = f"keyframes/frame_{s['id']:03}.jpg" if s["id"] <= 25 else "未抽取"
        lines.append(f"| {s['id']} | {s['start']:.3f} | {s['end']:.3f} | {s['duration']:.3f} | {key} |")
    (out / "timeline.md").write_text("\n".join(lines) + "\n")
    return {"duration": duration, "shot_candidates": len(shots), "out": str(out)}


PROFILE_FILES = ["style_analysis.md", "narrative_patterns.md", "cinematography.md", "editing_rhythm.md", "transitions.md", "typography.md", "audio_design.md", "anti_template_rules.md"]


def profile_init(out):
    out.mkdir(parents=True, exist_ok=True)
    targets = [out / "style_profile.json", *(out / name for name in PROFILE_FILES)]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError(f"风格档案目标文件已存在，拒绝覆盖: {', '.join(existing)}")
    put(out / "style_profile.json", {"schema_version": "1.0", "reference_account": {"url": "", "name": None, "verified": False}, "videos": [], "status": "pending_reference_video", "rules": [], "rule_schema": {"feature": "", "sources": [{"video": "", "start": 0, "end": 0}], "visual_audio_evidence": "", "conditions": "", "implementation": "", "avoid_when": "", "confidence": "low|medium|high", "status": "observed|inferred|pending"}})
    for name in PROFILE_FILES:
        (out / name).write_text(f"# {name[:-3]}\n\n待导入真实参考 MP4 后，按作品、时间码、画面和声音证据填写。\n")
    return str(out)


def validate_profile(directory):
    profile = json.loads((directory / "style_profile.json").read_text())
    errors = []
    fields = ["feature", "sources", "visual_audio_evidence", "conditions", "implementation", "avoid_when", "confidence", "status"]
    for i, rule in enumerate(profile.get("rules", []), 1):
        for field in fields:
            if field not in rule:
                errors.append(f"规则{i}缺少 {field}")
        if rule.get("status") not in {"observed", "inferred", "pending"}:
            errors.append(f"规则{i}状态无效")
        if rule.get("confidence") not in {"low", "medium", "high"}:
            errors.append(f"规则{i}可信度无效")
        if rule.get("status") == "observed" and (not rule.get("sources") or not rule.get("visual_audio_evidence")):
            errors.append(f"规则{i}标为已观察但缺少视频时间码或证据")
        for source in rule.get("sources", []):
            if not all(k in source for k in ["video", "start", "end"]):
                errors.append(f"规则{i}来源缺少视频或起止时间")
    return errors


PLAN_NAMES = ["director_brief", "shot_plan", "timeline", "typography_plan", "transition_plan", "audio_plan", "quality_checklist"]


def plan_init(out):
    out.mkdir(parents=True, exist_ok=True)
    targets = [out / f"{name}.json" for name in PLAN_NAMES]
    existing = [str(path) for path in targets if path.exists()]
    if existing:
        raise FileExistsError(f"导演方案目标文件已存在，拒绝覆盖: {', '.join(existing)}")
    base = {"schema_version": "1.0", "project": "", "target": {"width": 1080, "height": 1920, "fps": 30, "duration": None}, "topic": {"title": "", "github_skill": "", "verified_capabilities": [], "real_test_evidence": []}, "reference_profile": "", "opening_0_3s": "", "creative_rationale": "", "flow_use": {"needed": False, "reason": "", "authorized": False}}
    put(out / "director_brief.json", base)
    put(out / "shot_plan.json", {"shots": []})
    put(out / "timeline.json", {"schema_version": "1.0", "time_unit": "seconds", "shots": []})
    put(out / "typography_plan.json", {"rules": [], "events": []})
    put(out / "transition_plan.json", {"events": []})
    put(out / "audio_plan.json", {"music": {"source": "", "license": "", "tempo_hint_bpm": None}, "voiceover": [], "sfx": []})
    put(out / "quality_checklist.json", {"checks": [{"name": x, "status": "pending", "evidence": ""} for x in ["前2秒有可核验内容或结果线索", "真实功能有实测证据", "9:16画面文字可读", "素材与许可已核实", "镜头与音效有叙事用途", "无假冒实测的AI画面", "结尾无无效拖延"]]})
    return str(out)


REQUIRED = ["start", "end", "asset", "source_in", "source_out", "crop", "grade", "text_events", "transition_out", "sfx_events", "music_beat_reference", "voiceover", "narrative_goal"]


def validate_plan(directory, allow_missing=False):
    errors = []
    for name in PLAN_NAMES:
        if not (directory / f"{name}.json").is_file():
            errors.append(f"缺少 {name}.json")
    if errors:
        return errors
    brief = json.loads((directory / "director_brief.json").read_text())
    shots = json.loads((directory / "timeline.json").read_text())["shots"]
    if not shots:
        errors.append("时间线没有镜头")
    prior = 0.0
    for i, s in enumerate(shots, 1):
        for key in REQUIRED:
            if key not in s:
                errors.append(f"镜头{i}缺少 {key}")
        if any(k not in s for k in ["start", "end", "asset", "source_in", "source_out"]):
            continue
        a, b = s["start"], s["end"]
        if abs(a - prior) > 0.001:
            errors.append(f"镜头{i}与前镜头不连续: {prior} → {a}")
        if b <= a:
            errors.append(f"镜头{i}结束时间不大于开始时间")
        prior = b
        if s["source_out"] <= s["source_in"] or s["source_out"] - s["source_in"] + 0.001 < b - a:
            errors.append(f"镜头{i}原片区间不足")
        asset = s["asset"]
        if not all(k in asset for k in ["path", "type", "status"]):
            errors.append(f"镜头{i}素材缺少 path/type/status")
        elif asset["status"] not in {"ready", "missing"}:
            errors.append(f"镜头{i}素材状态无效: {asset['status']}（仅支持 ready/missing）")
        elif asset["status"] == "ready" and not (directory / asset["path"]).exists() and not Path(asset["path"]).exists():
            errors.append(f"镜头{i}素材不存在: {asset['path']}")
        elif asset["status"] == "missing" and not allow_missing:
            errors.append(f"镜头{i}素材待拍/待录")
    duration = brief.get("target", {}).get("duration")
    if duration is not None and shots and abs(prior - duration) > 0.001:
        errors.append(f"目标时长{duration}与时间线{prior}不符")
    topic = brief.get("topic", {})
    if not (topic.get("title") or topic.get("github_skill")):
        errors.append("未指定本期主题（填写 topic.title；旧项目可继续填写 github_skill）")
    return errors


def export_remotion(directory, out):
    errors = validate_plan(directory, allow_missing=True)
    if errors:
        raise ValueError("方案无效: " + "; ".join(errors))
    brief = json.loads((directory / "director_brief.json").read_text())
    fps = brief["target"]["fps"]
    shots = json.loads((directory / "timeline.json").read_text())["shots"]
    scenes = []
    for s in shots:
        scenes.append({"start_frame": round(s["start"] * fps), "end_frame": round(s["end"] * fps), "asset": s["asset"], "source_in": s["source_in"], "source_out": s["source_out"], "crop": s["crop"], "grade": s["grade"], "text_events": s["text_events"], "transition_out": s["transition_out"], "sfx_events": s["sfx_events"], "music_beat_reference": s["music_beat_reference"], "voiceover": s["voiceover"], "narrative_goal": s["narrative_goal"]})
    missing_assets = [scene["asset"].get("path", "") for scene in scenes if scene["asset"].get("status") != "ready"]
    put(out, {"format": "remotion-scene-handoff-v1", "fps": fps, "width": brief["target"]["width"], "height": brief["target"]["height"], "duration_in_frames": scenes[-1]["end_frame"], "scenes": scenes, "ready_to_render": not missing_assets, "missing_assets": missing_assets, "note": "导演决策输入；由 remotion-motion-graphics Skill 实现组件与渲染；该文件本身不是 Remotion 工程或成片"})
    return str(out)


def review(video, directory, out):
    out.mkdir(parents=True, exist_ok=True)
    info = probe(video)
    actual = video_duration(info)
    brief = json.loads((directory / "director_brief.json").read_text())
    target = brief["target"]
    stream = next(s for s in info["streams"] if s["codec_type"] == "video")
    findings = []
    if target["duration"] is not None and abs(actual - target["duration"]) > 0.2:
        findings.append({"timecode": round(min(actual, target["duration"]), 3), "issue": "成片时长与导演方案不符", "instruction": f"核对时间线并将成片调整到 {target['duration']} 秒", "basis": "ffprobe"})
    if (stream["width"], stream["height"]) != (target["width"], target["height"]):
        findings.append({"timecode": 0, "issue": "画幅与方案不符", "instruction": f"重新输出 {target['width']}×{target['height']} 并检查裁切", "basis": "ffprobe"})
    put(out / "review.json", {"video": str(video.resolve()), "actual_duration": actual, "findings": findings, "manual_review_required": ["逐段观看并听声：叙事、前2秒、主体裁切、花字、转场、调色、音乐、版权和结尾；每项补时间码与修改指令"]})
    return {"findings": len(findings), "out": str(out / "review.json")}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("analyze"); a.add_argument("video", type=Path); a.add_argument("--out", required=True, type=Path); a.add_argument("--threshold", type=float, default=0.32)
    a = sub.add_parser("profile-init"); a.add_argument("out", type=Path)
    a = sub.add_parser("validate-profile"); a.add_argument("directory", type=Path)
    a = sub.add_parser("plan-init"); a.add_argument("out", type=Path)
    a = sub.add_parser("validate-plan"); a.add_argument("directory", type=Path); a.add_argument("--allow-missing", action="store_true")
    a = sub.add_parser("export-remotion"); a.add_argument("directory", type=Path); a.add_argument("--out", required=True, type=Path)
    a = sub.add_parser("review"); a.add_argument("video", type=Path); a.add_argument("directory", type=Path); a.add_argument("--out", required=True, type=Path)
    args = p.parse_args()
    if args.cmd == "analyze": result = analyze(args.video, args.out, args.threshold)
    elif args.cmd == "profile-init": result = profile_init(args.out)
    elif args.cmd == "validate-profile":
        errors = validate_profile(args.directory)
        result = {"valid": not errors, "errors": errors}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if errors: raise SystemExit(1)
        return
    elif args.cmd == "plan-init": result = plan_init(args.out)
    elif args.cmd == "validate-plan":
        errors = validate_plan(args.directory, args.allow_missing)
        result = {"valid": not errors, "errors": errors}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if errors: raise SystemExit(1)
        return
    elif args.cmd == "export-remotion": result = export_remotion(args.directory, args.out)
    else: result = review(args.video, args.directory, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
