#!/usr/bin/env python3
"""Validate a Douyin automation project manifest without contacting platforms."""

from __future__ import annotations

import argparse
import json
import hashlib
import math
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from .creative_quality import validate_creative
except ImportError:
    from creative_quality import validate_creative


RESEARCH_STATUSES = {"verified", "limited", "unavailable", "not_requested"}
AUDIENCE_STATUSES = {"observed", "inferred", "unavailable"}
CLAIM_STATUSES = {"verified", "inferred", "unverified"}
ASSET_STATUSES = {"ready", "missing", "pending"}
EDIT_STATUSES = {"not_started", "blocked", "rendered", "qa_pass"}


def _is_object(value: Any) -> bool:
    return isinstance(value, dict)


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _has_timezone(value: Any) -> bool:
    if not _has_text(value):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _file_sha256(path: Path) -> str:
    if hasattr(hashlib, "file_digest"):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    h = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(65536):
            h.update(chunk)
    return h.hexdigest()


def validate_manifest(data: Any, root: Path | None = None, check_files: bool = False, stage: str = "auto") -> list[str]:
    errors: list[str] = []
    if not _is_object(data):
        return ["项目清单根节点必须是 JSON 对象"]

    project = data.get("project")
    if not _is_object(project):
        return ["缺少 project 对象"]
    for key in ("name", "topic"):
        if not _has_text(project.get(key)):
            errors.append(f"project.{key} 不能为空")
    platforms = project.get("platforms")
    if not isinstance(platforms, list) or not platforms or not all(_has_text(item) for item in platforms):
        errors.append("project.platforms 必须至少包含一个平台")
        platform_names: set[str] = set()
    else:
        platform_names = {item.strip().lower() for item in platforms}
    duration = project.get("duration_seconds")
    if not _is_number(duration) or duration <= 0:
        errors.append("project.duration_seconds 必须大于 0")
    frame = project.get("frame")
    if not _is_object(frame):
        errors.append("缺少 project.frame")
    else:
        width, height, fps = frame.get("width"), frame.get("height"), frame.get("fps")
        if not _is_number(width) or width <= 0 or not _is_number(height) or height <= 0:
            errors.append("project.frame.width/height 必须是正数")
        elif not _has_text(frame.get("aspect_ratio")) or ":" not in frame["aspect_ratio"]:
            errors.append("project.frame.aspect_ratio 必须写成例如 9:16 的比例")
        else:
            try:
                ratio_w, ratio_h = (float(x) for x in frame["aspect_ratio"].split(":", 1))
                if ratio_w <= 0 or ratio_h <= 0 or abs(width / height - ratio_w / ratio_h) > 0.01:
                    errors.append("project.frame 的像素尺寸与 aspect_ratio 不一致")
                if "douyin" in platform_names and abs(ratio_w / ratio_h - 9 / 16) > 0.001:
                    errors.append("抖音竖版视频默认应为 9:16")
            except ValueError:
                errors.append("project.frame.aspect_ratio 格式无效")
        if not _is_number(fps) or fps <= 0:
            errors.append("project.frame.fps 必须大于 0")

    research = data.get("research")
    if not _is_object(research):
        errors.append("缺少 research 对象")
        research = {}
    status = research.get("status")
    if status not in RESEARCH_STATUSES:
        errors.append(f"research.status 必须是 {sorted(RESEARCH_STATUSES)} 之一")
    sampled_at = research.get("sampled_at")
    if sampled_at is not None and not _has_timezone(sampled_at):
        errors.append("research.sampled_at 必须是带时区的 ISO 8601 时间")
    limitations = research.get("limitations", [])
    if not isinstance(limitations, list) or not all(_has_text(item) for item in limitations):
        errors.append("research.limitations 必须是文字数组")
        limitations = []
    if status in {"limited", "unavailable"} and not limitations:
        errors.append(f"research.status={status} 时必须说明限制")

    sources = research.get("sources", [])
    if not isinstance(sources, list):
        errors.append("research.sources 必须是数组")
        sources = []
    source_ids: set[str] = set()
    target_metric_count = 0
    for index, source in enumerate(sources, 1):
        label = f"research.sources[{index - 1}]"
        if not _is_object(source):
            errors.append(f"{label} 必须是对象")
            continue
        source_id = source.get("source_id")
        if not _has_text(source_id):
            errors.append(f"{label}.source_id 不能为空")
        elif source_id in source_ids:
            errors.append(f"{label}.source_id 重复: {source_id}")
        else:
            source_ids.add(source_id)
        if not _has_text(source.get("platform")) or not _has_text(source.get("title")):
            errors.append(f"{label} 必须有 platform 和 title")
        url = source.get("url")
        if not _has_text(url) or not url.startswith(("https://", "http://")):
            errors.append(f"{label}.url 必须是 http(s) 链接")
        if not _has_timezone(source.get("observed_at")):
            errors.append(f"{label}.observed_at 必须是带时区的 ISO 8601 时间")
        published_at = source.get("published_at")
        if published_at is not None and not _has_timezone(published_at):
            errors.append(f"{label}.published_at 格式无效，未知时应留空")
        audience = source.get("audience")
        if not _is_object(audience) or audience.get("status") not in AUDIENCE_STATUSES:
            errors.append(f"{label}.audience.status 必须是 {sorted(AUDIENCE_STATUSES)} 之一")
        elif not _has_text(audience.get("basis")):
            errors.append(f"{label}.audience.basis 不能为空；不可得时说明原因")
        metrics = source.get("metrics", [])
        if not isinstance(metrics, list):
            errors.append(f"{label}.metrics 必须是数组")
            continue
        if str(source.get("platform", "")).strip().lower() in platform_names:
            target_metric_count += len(metrics)
        for metric_index, metric in enumerate(metrics, 1):
            if not _is_object(metric):
                errors.append(f"{label}.metrics[{metric_index - 1}] 必须是对象")
                continue
            for key in ("name", "raw_value", "unit"):
                if key not in metric or metric[key] is None or (isinstance(metric[key], str) and not metric[key].strip()):
                    errors.append(f"{label}.metrics[{metric_index - 1}].{key} 必须保留原始值")
            if not _has_timezone(metric.get("observed_at")):
                errors.append(f"{label}.metrics[{metric_index - 1}].observed_at 必须带时区")
    has_target_platform_source = any(
        _is_object(source) and str(source.get("platform", "")).strip().lower() in platform_names
        for source in sources
    )
    if status == "verified" and (not has_target_platform_source or target_metric_count == 0):
        errors.append("research.status=verified 需要目标平台来源和至少一项带时间的可见指标")

    script = data.get("script")
    if not _is_object(script):
        errors.append("缺少 script 对象")
        script = {}
    if not _has_text(script.get("hook")):
        errors.append("script.hook 不能为空")
    claims = script.get("claims", [])
    if not isinstance(claims, list):
        errors.append("script.claims 必须是数组")
        claims = []
    claim_ids: set[str] = set()
    for index, claim in enumerate(claims, 1):
        label = f"script.claims[{index - 1}]"
        if not _is_object(claim):
            errors.append(f"{label} 必须是对象")
            continue
        claim_id = claim.get("claim_id")
        if not _has_text(claim_id) or claim_id in claim_ids:
            errors.append(f"{label}.claim_id 不能为空且不得重复")
        else:
            claim_ids.add(claim_id)
        if not _has_text(claim.get("text")) or claim.get("status") not in CLAIM_STATUSES:
            errors.append(f"{label} 必须包含 text 和有效 status")
        refs = claim.get("evidence_source_ids", [])
        if not isinstance(refs, list) or not all(isinstance(item, str) for item in refs):
            errors.append(f"{label}.evidence_source_ids 必须是 ID 数组")
            refs = []
        for source_id in refs:
            if source_id not in source_ids:
                errors.append(f"{label} 引用不存在的来源 {source_id}")
        if claim.get("status") == "verified" and not refs:
            errors.append(f"{label} 标为 verified 但没有来源")

    director = data.get("director", {})
    if not _is_object(director):
        errors.append("director 必须是对象")
        director = {}
    covers = director.get("covers", [])
    if not isinstance(covers, list):
        errors.append("director.covers 必须是数组")
        covers = []
    expected_covers = {"horizontal": (1440, 1080, "4:3"), "vertical": (1080, 1440, "3:4")}
    for cover in covers:
        if not _is_object(cover):
            errors.append("director.covers 元素必须是对象")
            continue
        name = cover.get("name")
        if name in expected_covers:
            expected = expected_covers[name]
            if (cover.get("width"), cover.get("height"), cover.get("aspect_ratio")) != expected:
                errors.append(f"封面 {name} 必须为 {expected[2]} {expected[0]}×{expected[1]}")
    if "douyin" in platform_names:
        cover_names = {cover.get("name") for cover in covers if _is_object(cover)}
        if not set(expected_covers).issubset(cover_names):
            errors.append("抖音项目需要同时记录横版和竖版封面规格")

    shots = director.get("shots", [])
    if not isinstance(shots, list):
        errors.append("director.shots 必须是数组")
        shots = []
    previous_end: float | None = None
    all_assets_ready = bool(shots)
    for index, shot in enumerate(shots, 1):
        label = f"director.shots[{index - 1}]"
        if not _is_object(shot):
            errors.append(f"{label} 必须是对象")
            all_assets_ready = False
            continue
        start, end = shot.get("start"), shot.get("end")
        if not _is_number(start) or not _is_number(end) or start < 0 or end <= start:
            errors.append(f"{label} 起止时间无效")
        elif previous_end is not None and abs(start - previous_end) > 0.01:
            errors.append(f"{label} 与前一镜头不连续")
        if _is_number(end):
            previous_end = end
        asset = shot.get("asset")
        if not _is_object(asset) or asset.get("status") not in ASSET_STATUSES:
            errors.append(f"{label}.asset.status 必须是 {sorted(ASSET_STATUSES)} 之一")
            all_assets_ready = False
            continue
        if asset.get("status") != "ready":
            all_assets_ready = False
        if asset.get("status") == "ready":
            path = asset.get("path")
            if not _has_text(path):
                errors.append(f"{label} 已就绪素材必须有 path")
                all_assets_ready = False
            elif check_files and root is not None and not (root / path).expanduser().exists():
                errors.append(f"{label} 声明素材就绪但文件不存在: {path}")
        refs = shot.get("claim_ids", [])
        if isinstance(refs, list):
            for claim_id in refs:
                if claim_id not in claim_ids:
                    errors.append(f"{label} 引用不存在的主张 {claim_id}")
    if shots and _is_number(duration) and previous_end is not None and abs(previous_end - duration) > 0.01:
        errors.append("分镜总时长与 project.duration_seconds 不一致")

    editing = data.get("editing")
    if not _is_object(editing):
        errors.append("缺少 editing 对象")
        editing = {}
    edit_status = editing.get("status")
    if edit_status not in EDIT_STATUSES:
        errors.append(f"editing.status 必须是 {sorted(EDIT_STATUSES)} 之一")
    if edit_status in {"rendered", "qa_pass"}:
        for key in ("render_path", "editable_project_path"):
            if not _has_text(editing.get(key)):
                errors.append(f"editing.status={edit_status} 时必须提供 {key}")
        if not all_assets_ready:
            errors.append(f"editing.status={edit_status} 但存在未就绪镜头素材")
    if edit_status == "qa_pass":
        technical = editing.get("technical_qa", {})
        human = editing.get("human_review", {})
        if not _is_object(technical) or technical.get("status") != "passed":
            errors.append("editing.status=qa_pass 需要技术 QA 通过")
        if editing.get("engine") == "remotion":
            automated = editing.get("automated_review", {})
            if not _is_object(automated) or automated.get("status") != "passed":
                errors.append("Remotion 无人值守成片需要真实音画自动审查，不能只靠机器预检")
            elif not _has_text(automated.get("reviewer")) or not _has_timezone(automated.get("reviewed_at")) or not _has_text(automated.get("evidence")):
                errors.append("自动音画审查缺检查人、时间或实际观察证据")
        elif not _is_object(human) or human.get("status") != "passed":
            errors.append("editing.status=qa_pass 需要人工完整观看/听声通过")
        elif not _has_text(human.get("reviewer")) or not _has_timezone(human.get("reviewed_at")):
            errors.append("人工 QA 通过必须记录检查人和带时区的检查时间")

    delivery = data.get("delivery")
    if not _is_object(delivery):
        errors.append("缺少 delivery 对象")
    else:
        if delivery.get("status") not in {"pending", "ready", "blocked"}:
            errors.append("delivery.status 必须是 pending、ready 或 blocked")
        if delivery.get("status") == "ready" and edit_status != "qa_pass":
            errors.append("delivery.status=ready 需要 editing.status=qa_pass")
        if delivery.get("manual_publish_only") is True and delivery.get("published") is True:
            errors.append("本账号只能用户亲自发布，生产 Skill 不允许标记为已发布")
        if delivery.get("published") is True and delivery.get("publish_authorized") is not True:
            errors.append("标记已发布时必须记录 publish_authorized=true")

    if check_files and root is not None and edit_status in {"rendered", "qa_pass"}:
        for key in ("render_path", "editable_project_path"):
            path = editing.get(key)
            if _has_text(path) and not (root / path).expanduser().exists():
                errors.append(f"声明交付文件不存在: {key}={path}")
    if edit_status == "blocked":
        for key in ("blocker", "recovery_action"):
            if not _has_text(editing.get(key)):
                errors.append(f"剪辑受阻必须记录 {key}")
    if check_files and root is not None and (edit_status == "qa_pass" or stage == "final"):
        review = editing.get("creative_review")
        review = review if _is_object(review) else {}
        render = editing.get("render_path")
        if _has_text(render):
            path = (root / render).expanduser()
            if path.is_file():
                try:
                    actual = _file_sha256(path)
                    if review.get("render_sha256") != actual:
                        errors.append("创意验收成片 SHA256 不匹配，须重新看听本次导出")
                except OSError as exc:
                    errors.append(f"无法核验成片: {exc}")
    errors.extend(validate_creative(data, stage))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="project-manifest.json 路径")
    parser.add_argument("--root", type=Path, help="素材和交付文件的项目根目录；默认使用清单所在目录")
    parser.add_argument("--check-files", action="store_true", help="检查标记为 ready/rendered 的本地文件")
    parser.add_argument("--stage", choices=["auto", "script", "director", "edit", "final"], default="auto", help="制作阶段门槛；auto 在渲染/交付状态强制检查")
    args = parser.parse_args()
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2
    root = args.root or args.manifest.parent
    errors = validate_manifest(data, root=root, check_files=args.check_files, stage=args.stage)
    print(json.dumps({"valid": not errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
