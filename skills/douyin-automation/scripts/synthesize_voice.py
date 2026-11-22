#!/usr/bin/env python3
"""Produce an offline Chinese voiceover on macOS without a paid API."""
import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def voices():
    result = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("无法查询 macOS 可用语音")
    choices = []
    for line in result.stdout.splitlines():
        if "zh_CN" in line or "zh_TW" in line or "zh_HK" in line:
            choices.append(line.split()[0])
    return choices


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("script", type=Path, help="要朗读的纯文本 UTF-8 脚本")
    p.add_argument("output", type=Path, help="输出 WAV 文件（推荐放 remotion/public/voice.wav）")
    p.add_argument("--voice", help="可用 macOS 中文 voice 名，默认自动选择")
    args = p.parse_args()
    try:
        if not shutil.which("say") or not shutil.which("ffmpeg"):
            raise RuntimeError("该离线配音需要 macOS say 与 ffmpeg；当前系统不支持")
        text = args.script.read_text(encoding="utf-8").strip()
        if not text or len(text) > 4000:
            raise RuntimeError("配音文本不能为空，单次最多 4000 字")
        allowed = voices()
        if not allowed:
            raise RuntimeError("未发现已安装的 macOS 中文音色；安装中文语音或配置获授权的 TTS")
        name = args.voice or allowed[0]
        if name not in allowed:
            raise RuntimeError(f"指定中文音色未安装：{name}；可用音色: {allowed}")
        target = args.output.expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        source = target.with_suffix(".aiff")
        try:
            subprocess.run(["say", "-v", name, "-f", str(args.script), "-o", str(source)],
                           check=True, capture_output=True, text=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i",
                            str(source), "-ar", "48000", "-ac", "2", str(target)],
                           check=True, capture_output=True, text=True)
        finally:
            source.unlink(missing_ok=True)
        print(json.dumps({"status": "generated", "engine": "macos_say",
                          "voice": name, "path": str(target), "published": False}, ensure_ascii=False))
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError) as err:
        print(json.dumps({"status": "blocked", "error": str(err)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
