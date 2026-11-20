#!/usr/bin/env python3
"""Inspect rendered media metadata with ffprobe; visual review remains manual."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    try:
        numerator, denominator = value.split("/", 1)
        divisor = float(denominator)
        return float(numerator) / divisor if divisor else None
    except (ValueError, ZeroDivisionError):
        try:
            return float(value)
        except ValueError:
            return None


def inspect_probe(
    payload: dict[str, Any],
    expect_width: int | None = None,
    expect_height: int | None = None,
    expect_duration: float | None = None,
    require_audio: bool = False,
) -> dict[str, Any]:
    streams = payload.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    fmt = payload.get("format", {})
    duration = None
    try:
        duration = float(fmt.get("duration"))
    except (TypeError, ValueError):
        try:
            duration = float(video.get("duration")) if video else None
        except (TypeError, ValueError):
            duration = None
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "status": "passed" if passed else "failed", "detail": detail})

    record("video_stream", video is not None, "找到视频流" if video else "没有视频流")
    if video:
        width, height = video.get("width"), video.get("height")
        record("dimensions", bool(width and height), f"{width}×{height}")
        fps = _rate(video.get("avg_frame_rate") or video.get("r_frame_rate"))
        record("frame_rate", fps is not None and fps > 0, f"{fps:g} fps" if fps else "帧率未知")
        if expect_width is not None and expect_height is not None:
            record(
                "expected_dimensions",
                (width, height) == (expect_width, expect_height),
                f"实际 {width}×{height}；目标 {expect_width}×{expect_height}",
            )
    record("duration", duration is not None and duration > 0, f"{duration:g} 秒" if duration else "时长未知")
    if expect_duration is not None:
        record(
            "expected_duration",
            duration is not None and abs(duration - expect_duration) <= 0.2,
            f"实际 {duration:g} 秒；目标 {expect_duration:g} 秒" if duration is not None else "时长未知",
        )
    if require_audio:
        record("audio_stream", audio is not None, "找到音频流" if audio else "要求有音频但未找到")
    return {
        "technical_status": "passed" if all(check["status"] == "passed" for check in checks) else "failed",
        "file": payload.get("_file"),
        "duration_seconds": duration,
        "video": {
            "width": video.get("width") if video else None,
            "height": video.get("height") if video else None,
            "fps": _rate((video or {}).get("avg_frame_rate") or (video or {}).get("r_frame_rate")),
            "codec": (video or {}).get("codec_name"),
        },
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "checks": checks,
        "manual_review_required": [
            "从头到尾观看：事实、字幕、画面可读性、裁切、黑帧、节奏和转场",
            "从头到尾听声：口播清晰度、音画同步、音乐/音效和削波",
        ],
        "note": "ffprobe 只检查媒体结构和元数据；不能判定画面质量、内容真实性、版权或人工观看结果。",
    }


def inspect_file(path: Path, **expectations: Any) -> dict[str, Any]:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise RuntimeError("需要 ffprobe 才能检查渲染文件")
    if not path.is_file():
        raise FileNotFoundError(f"视频文件不存在: {path}")
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    payload["_file"] = str(path.resolve())
    return inspect_probe(payload, **expectations)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path, help="MP4 或其他 ffprobe 可读取的视频文件")
    parser.add_argument("--expect-width", type=int)
    parser.add_argument("--expect-height", type=int)
    parser.add_argument("--expect-duration", type=float)
    parser.add_argument("--require-audio", action="store_true")
    args = parser.parse_args()
    if (args.expect_width is None) != (args.expect_height is None):
        parser.error("--expect-width 和 --expect-height 必须同时提供")
    try:
        report = inspect_file(
            args.video,
            expect_width=args.expect_width,
            expect_height=args.expect_height,
            expect_duration=args.expect_duration,
            require_audio=args.require_audio,
        )
    except (OSError, RuntimeError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(json.dumps({"technical_status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["technical_status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
