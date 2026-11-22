#!/usr/bin/env python3
"""Generate Chinese AI narration through Qwen3-TTS MLX, never macOS say."""
import argparse
import json
import platform
import subprocess
import sys
from pathlib import Path

MODEL = "mlx-community/Qwen3-TTS-12Hz-0.6B-CustomVoice-4bit"
VOICES = ("Uncle_Fu", "Vivian", "Serena", "Eric", "Dylan")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path, help="UTF-8 Chinese narration")
    parser.add_argument("output", type=Path, help="Output WAV (remotion/public/voice.wav)")
    parser.add_argument("--voice", choices=VOICES, default="Uncle_Fu")
    parser.add_argument("--instruct", default="natural friendly conversational Mandarin explainer; clear, not robotic")
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    try:
        if platform.system() != "Darwin" or platform.machine() != "arm64":
            raise RuntimeError("Qwen MLX requires Apple Silicon macOS; no system-voice fallback")
        text = args.script.expanduser().read_text(encoding="utf-8").strip()
        if not text or len(text) > 4000:
            raise RuntimeError("script must contain 1–4000 characters")
        try:
            from mlx_audio.tts.generate import generate_audio
        except ImportError as exc:
            raise RuntimeError("mlx-audio unavailable; install separately via python3 -m pip install mlx-audio soundfile") from exc
        output = args.output.expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        generate_audio(text=text, model=args.model, voice=args.voice, instruct=args.instruct,
                       lang_code="chinese", speed=1.0, output_path=str(output.parent),
                       file_prefix=output.stem, audio_format="wav", join_audio=True,
                       play=False, verbose=False)
        if not output.is_file() or output.stat().st_size < 4096:
            raise RuntimeError("model did not produce a valid-sized WAV output")
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "json", str(output)],
                               capture_output=True, text=True, check=True)
        seconds = float(json.loads(probe.stdout)["format"]["duration"])
        if seconds < 1:
            raise RuntimeError("audio duration is too short")
        print(json.dumps({"status": "generated", "engine": "qwen3_tts_mlx",
                          "voice": args.voice, "path": str(output),
                          "duration_seconds": seconds, "published": False}, ensure_ascii=False))
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc),
                          "no_system_voice_fallback": True}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
