#!/usr/bin/env python3
"""Autonomous Remotion build gate. Never publishes or controls social accounts."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates/remotion"
FILES = ("animation.jsx", "timeline.mjs", "check-timeline.mjs",
         "motion-timeline.json", "package.json", "package-lock.json")


class GateError(Exception):
    pass


def run(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode:
        raise GateError(f"{args[0]} 失败: {(result.stderr or result.stdout)[-1800:]}")
    return result.stdout


def initialize(project):
    workspace = project / "remotion"
    workspace.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        source, dest = TEMPLATE / name, workspace / name
        if not source.is_file():
            raise GateError(f"缺少模板: {source}")
        if not dest.exists():
            shutil.copy2(source, dest)
    (workspace / "public").mkdir(exist_ok=True)
    (project / "delivery").mkdir(exist_ok=True)


def check_timeline(workspace):
    plan = json.loads((workspace / "motion-timeline.json").read_text(encoding="utf-8"))
    fps, duration = plan.get("fps"), plan.get("duration")
    if not isinstance(fps, int) or not 24 <= fps <= 60 or not isinstance(duration, int) or duration < 1:
        raise GateError("fps/duration 无效")
    shots, tracks = plan.get("shots"), plan.get("audio")
    if not isinstance(shots, list) or not shots or not isinstance(tracks, list):
        raise GateError("缺少 shots/audio")
    if not any(t.get("role") == "voice" for t in tracks if isinstance(t, dict)):
        raise GateError("正式成片必须具有真实 voice 音轨")
    cursor, real, photos = 0, 0, set()
    for idx, shot in enumerate(shots, 1):
        if not isinstance(shot, dict):
            raise GateError(f"镜头 {idx} 结构无效")
        begin, end = shot.get("from"), shot.get("to")
        if not isinstance(begin, int) or not isinstance(end, int) or begin != cursor or end <= begin:
            raise GateError(f"镜头 {idx} 断帧/时长错误")
        cursor = end
        if shot.get("origin") == "capture" and shot.get("type") in ("image", "video"):
            for key in ("source", "source_identity", "rights"):
                if not isinstance(shot.get(key), str) or not shot[key].strip():
                    raise GateError(f"实录镜头 {idx} 缺少 {key}")
            if shot.get("type") == "image":
                if shot["source_identity"] in photos:
                    raise GateError("同一真实照片不得重复使用")
                photos.add(shot["source_identity"])
            real += end - begin
    if cursor != duration:
        raise GateError("镜头无法覆盖全部帧")
    ratio = real / duration
    if ratio <= .5:
        raise GateError(f"真实素材主体时长必须 > 50%，当前 {ratio:.1%}")
    return {"fps": fps, "frames": duration, "seconds": duration / fps,
            "real_ratio": ratio, "shots": len(shots)}


def render(project, dry_run=False, skip_install=False):
    workspace, delivery = project / "remotion", project / "delivery"
    if not workspace.is_dir():
        raise GateError("请先 init 项目")
    info = check_timeline(workspace)
    # The template writes SRT with exclusive-create; remove only its generated output for re-runs.
    (workspace / "字幕.srt").unlink(missing_ok=True)
    run(["node", "check-timeline.mjs"], workspace)
    if dry_run:
        return {"status": "preflight_passed", "rendered": False, **info}
    if not (workspace / "node_modules").exists():
        if skip_install:
            raise GateError("缺少 Remotion node_modules")
        run(["npm", "ci"], workspace)
    delivery.mkdir(exist_ok=True)
    video = delivery / "视频-待人工发布.mp4"
    run(["npm", "run", "render", "--", str(video)], workspace)
    report = json.loads(run(["ffprobe", "-v", "error", "-show_streams",
                             "-show_format", "-of", "json", str(video)], workspace))
    v = next((x for x in report.get("streams", []) if x.get("codec_type") == "video"), None)
    audio = any(x.get("codec_type") == "audio" for x in report.get("streams", []))
    seconds = float(report.get("format", {}).get("duration") or 0)
    if not v or (v.get("width"), v.get("height")) != (1080, 1920) or not audio:
        raise GateError("需要实际 1080x1920 视频与音频轨")
    if abs(seconds - info["seconds"]) > .12:
        raise GateError("成片时长与时间轴不一致")
    images = delivery / "抽帧审查"
    images.mkdir(exist_ok=True)
    run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(video), "-vf", "fps=1,scale=540:-1", "-frames:v", "120",
         str(images / "%04d.jpg")], workspace)
    shutil.copy2(workspace / "字幕.srt", delivery / "字幕.srt")
    machine = {"rendered_at": datetime.now(timezone.utc).isoformat(),
               "engine": "remotion", "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
               "video_path": str(video), "has_audio": audio, "duration_seconds": seconds,
               "timeline": info, "machine_status": "passed",
               "visual_review": "not_run", "audio_review": "not_run",
               "manual_publish_only": True, "published": False,
               "note": "抽帧和 ffprobe 不是观感或事实审查；应真实查看/听取导出视频。"}
    (delivery / "machine-qa.json").write_text(
        json.dumps(machine, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "rendered_needs_review", "path": str(video), **info}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["init", "render"])
    parser.add_argument("project", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-install", action="store_true")
    args = parser.parse_args()
    try:
        project = args.project.expanduser().resolve()
        result = (initialize(project) or {"status": "initialized", "project": str(project)}) if args.mode == "init" else render(project, args.dry_run, args.skip_install)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (GateError, OSError, ValueError, json.JSONDecodeError) as error:
        print(json.dumps({"status": "blocked", "error": str(error),
                          "published": False}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
