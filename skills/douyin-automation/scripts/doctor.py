#!/usr/bin/env python3
"""Environment and prerequisite doctor for douyin-automation."""
import json
import shutil
import subprocess
import sys
from pathlib import Path


def check_tool(name: str, min_version_hint: str = "") -> tuple[bool, str]:
    path = shutil.which(name)
    if not path:
        return False, "未安装"
    try:
        ver = subprocess.run([name, "-version"], capture_output=True, text=True)
        if ver.returncode == 0:
            first_line = ver.stdout.splitlines()[0] if ver.stdout else ""
            return True, f"{path} ({first_line[:40]})"
    except Exception:
        pass
    return True, path


def main() -> int:
    print("=== douyin-automation 环境自检 (Doctor) ===")
    all_ok = True

    # 1. Python
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    if sys.version_info >= (3, 11):
        print(f"[\033[32m✓\033[0m] Python {py_ver} (满足 >= 3.11 要求)")
    elif sys.version_info >= (3, 9):
        print(f"[\033[33m!\033[0m] Python {py_ver} (已通过兼容层支持，建议升级至 >= 3.11)")
    else:
        print(f"[\033[31m✗\033[0m] Python {py_ver} (过低，需要 >= 3.9)")
        all_ok = False

    # 2. Media tools
    for tool in ("ffmpeg", "ffprobe"):
        ok, msg = check_tool(tool)
        if ok:
            print(f"[\033[32m✓\033[0m] {tool}: {msg}")
        else:
            print(f"[\033[31m✗\033[0m] {tool}: 缺失！视频分析、自动剪辑与质检必须依赖 {tool}")
            all_ok = False

    # 3. Node.js
    node_ok, node_msg = check_tool("node")
    if node_ok:
        print(f"[\033[32m✓\033[0m] Node.js: {node_msg}")
    else:
        print(f"[\033[33m!\033[0m] Node.js 未找到 (技术讲解 inspect_technical.mjs 与 Remotion 需要 Node.js)")

    # 4. Swift
    swift_ok, swift_msg = check_tool("swift")
    if swift_ok:
        print(f"[\033[32m✓\033[0m] Swift: {swift_msg} (支持 macOS 原生高保真花字/气泡渲染)")
    else:
        print(f"[\033[33m!\033[0m] Swift 未找到 (当前 draw_overlay.swift 依赖 macOS Swift/AppKit)")

    # 5. Templates check
    repo_root = Path(__file__).resolve().parents[1]
    manifest = repo_root / "templates" / "project-manifest.json"
    if manifest.is_file():
        try:
            json.loads(manifest.read_text(encoding="utf-8"))
            print(f"[\033[32m✓\033[0m] 模版 project-manifest.json 格式正常")
        except Exception as e:
            print(f"[\033[31m✗\033[0m] 模版 project-manifest.json 解析失败: {e}")
            all_ok = False
    else:
        print(f"[\033[31m✗\033[0m] 模版缺失: {manifest}")
        all_ok = False

    print("===========================================")
    if all_ok:
        print("\033[32m核心依赖就绪，可以执行视频制作与质检流程！\033[0m")
        return 0
    else:
        print("\033[31m存在核心依赖缺失，请先安装对应工具后再运行。\033[0m")
        return 1


if __name__ == "__main__":
    sys.exit(main())
