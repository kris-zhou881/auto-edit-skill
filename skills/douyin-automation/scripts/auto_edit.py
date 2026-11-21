#!/usr/bin/env python3
"""Assemble shot-level media and narration, run quality gates, and save edit assets."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

FPS = 30
WIDTH, HEIGHT = 1080, 1920
VISUAL = (76, 325, 804, 990)
CAPTION = (76, 1380, 804, 230)
SAFE = (64, 125, 840, 1515)
SCRIPT = Path(__file__).parent


def command(*args, binary=False):
    result = subprocess.run(list(map(str, args)), capture_output=True)
    if result.returncode:
        raise ValueError(result.stderr.decode(errors="replace").strip() or "命令失败")
    return result.stdout if binary else result.stdout.decode()


def ff(*args):
    command("ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", *args)


def media(path):
    return json.loads(command("ffprobe", "-v", "error", "-show_streams",
                              "-show_format", "-of", "json", path))


def measured(path, filters):
    result = subprocess.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", str(path),
                             "-vn", "-af", filters, "-f", "null", "-"],
                            capture_output=True, text=True, check=True)
    return result.stderr


def silence(path, minimum=0.80):
    log = measured(path, f"silencedetect=n=-42dB:d={minimum}")
    starts = re.findall(r"silence_start: ([\d.]+)", log)
    ends = re.findall(r"silence_end: ([\d.]+)", log)
    return [[float(a), float(b)] for a, b in zip(starts, ends)]


def db(path):
    log = measured(path, "volumedetect")
    return tuple(float(re.search(rf"{key}_volume: ([\d.-]+) dB", log)[1])
                 for key in ("mean", "max"))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def timeline(plan, root, out):
    shots, frame, assets = [], 0, out / "素材"
    assets.mkdir(exist_ok=True)
    if len(plan["shots"]) < 2 or plan["shots"][0]["type"] in {"concept_card", "legacy_example"}:
        raise ValueError("必须有镜头区分，首镜使用真实结果或过程")
    voice_mode = plan.get("voice_mode", "jianying_free")
    if voice_mode not in {"jianying_free", "local_preview"}:
        raise ValueError("未知配音来源")
    if voice_mode == "jianying_free":
        evidence = plan.get("voice_evidence")
        if not isinstance(evidence, dict) or not evidence.get("name") or not evidence.get("path"):
            raise ValueError("需要剪映免费音色名称及实测证据")
        (root / evidence["path"]).resolve(strict=True)
        if any(not shot.get("voice_file") for shot in plan["shots"]):
            raise ValueError("缺少从剪映生成的分句音频；不使用系统音色替代")
    required = {"type", "source", "voice_text", "caption", "emphasis",
                "motion", "transition", "sound", "role"}
    for position, shot in enumerate(plan["shots"], 1):
        missing = required - shot.keys()
        if missing or any(not shot[key] for key in required):
            raise ValueError(f"镜头 {position} 缺字段或内容: {sorted(missing)}")
        if shot["type"] not in {"screen_recording", "live_action", "operation_demo",
                                "data_visualization", "legacy_example", "concept_card"}:
            raise ValueError(f"未知画面类型 {shot['type']}")
        if shot["transition"] not in {"cut", "dip", "light_dip"} or shot["motion"] not in {"source", "focus", "push"}:
            raise ValueError("未知转场或运镜")
        if shot["sound"] not in {"none", "tick", "click"}:
            raise ValueError("未知音效")
        source = (root / shot["source"]).resolve(strict=True)
        sid = f"{position:02d}"
        voice = assets / f"{sid}-口播.wav"
        original = assets / f"{sid}-原声.wav"
        if shot.get("voice_file"):
            original = (root / shot["voice_file"]).resolve(strict=True)
        else:
            command("say", "-v", plan.get("voice", "Tingting"), "-r",
                    plan.get("words_per_minute", 205), "-o", original,
                    "--data-format=LEI16@44100", shot["voice_text"])
        source_duration = float(media(original)["format"]["duration"])
        quiet = silence(original, .04)
        start = max(0, quiet[0][1] - .02) if quiet and quiet[0][0] < .012 else 0
        end = min(source_duration, quiet[-1][0]+.075) if quiet and quiet[-1][1] >= source_duration-.02 else source_duration
        if end <= start:
            raise ValueError(f"镜头 {sid} 配音为空")
        ff("-i", original, "-af", f"atrim=start={start}:end={end},asetpts=PTS-STARTPTS,alimiter=limit=0.75:level=0",
           "-ac", 1, "-ar", 48000, voice)
        voice_duration = float(media(voice)["format"]["duration"])
        if voice_duration < .32:
            raise ValueError(f"镜头 {sid} 缺少有效语音")
        frames = math.ceil((voice_duration + min(.35, max(0, shot.get("pause", .14)))) * FPS)
        if shot["type"] in {"concept_card", "legacy_example"} and frames > 4 * FPS:
            raise ValueError(f"镜头 {sid} 的静态卡或旧片举例超过四秒")
        if position == 1 and frames > 3 * FPS:
            raise ValueError("前三秒应完成开场钩子，请缩短第一句")
        seconds = frames / FPS
        event = shot.get("click_event")
        if event is not None:
            if not isinstance(event, dict) or any(type(event.get(k)) is not int for k in ("frame", "x", "y")):
                raise ValueError(f"镜头 {sid} 点击须提供整数帧、x 和 y")
            if not 8 <= event["frame"] <= frames - 10 or not 120 <= event["x"] <= 815 or not 370 <= event["y"] <= 1260:
                raise ValueError(f"镜头 {sid} 点击超出主体安全区或距切点太近")
        if (shot["sound"] == "click") != (event is not None):
            raise ValueError(f"镜头 {sid} 点击画面与音效必须共用同一 click_event")
        start = float(shot.get("in", 0))
        if start < 0 or not math.isfinite(start):
            raise ValueError(f"镜头 {sid} 素材起点无效")
        if shot["type"] != "concept_card":
            info = media(source)
            if not any(x["codec_type"] == "video" for x in info["streams"]):
                raise ValueError(f"镜头 {sid} 缺少视频流")
            if float(info["format"]["duration"]) + .034 < start + seconds:
                raise ValueError(f"镜头 {sid} 素材不足 {seconds:.2f} 秒")
        frame_end = frame + frames
        shots.append(dict(shot, id=sid, source=str(source), voice_file=str(voice),
                          start=frame/FPS, end=frame_end/FPS,
                          frames=frames, duration=seconds, voice_duration=voice_duration))
        frame = frame_end
    if sum(s["duration"] for s in shots if s["type"] in {"concept_card", "legacy_example"}) / (frame/FPS) > .25:
        raise ValueError("静态卡和旧稿举例超过总时长的 25%")
    return shots


def caption_lines(text, limit):
    if "\n" in text:
        return text.splitlines()
    lines = []
    while text:
        if len(text) <= limit:
            return lines + [text]
        boundary = max((i+1 for i, c in enumerate(text[:limit]) if c in "，、：。！？ " and i >= 6), default=limit)
        lines.append(text[:boundary].strip())
        text = text[boundary:].strip()
    return lines


def concat(parts, output, folder):
    listing = folder / (output.stem + "-concat.txt")
    listing.write_text("".join(f"file '{x.name}'\n" for x in parts))
    ff("-f", "concat", "-safe", 0, "-i", listing, "-c", "copy", output)


def render(plan, shots, out, attempt):
    assets = out / "素材"
    overlays = []
    for s in shots:
        sid = s["id"]
        lines = caption_lines(s.get("retry_caption", s["caption"]) if attempt else s["caption"], 14)
        if not 1 <= len(lines) <= 2 or any(len(line) > 14 for line in lines):
            raise ValueError(f"镜头 {sid} 字幕过长；提供精简的 retry_caption")
        s["rendered_caption"] = lines
        for kind, headline, content in [
            ("caption", s["emphasis"], lines), ("header", s["role"], [s.get("label", "")])
        ]:
            path = assets / f"{sid}-{kind}.png"
            overlays.append(dict(mode=kind, headline=headline, lines=content,
                                 accent=s.get("accent", ""), output=str(path),
                                 style=plan.get("caption_style"), keyword=s.get("caption_keyword"),
                                 backdrop=s.get("backdrop", plan.get("backdrop"))))
    if any(s.get("click_event") for s in shots):
        overlays.append(dict(mode="cursor", headline="", lines=[], accent="",
                             output=str(assets / "cursor.png")))
    spec = assets / "overlays.json"
    write_json(spec, overlays)
    command("swift", SCRIPT / "draw_overlay.swift", spec)

    raw, styled, voices, effects = [], [], [], []
    for s in shots:
        sid, n, duration = s["id"], s["frames"], s["duration"]
        clip = assets / f"{sid}-画面.mp4"
        boxed = assets / f"{sid}-预览.mp4"
        voice = assets / f"{sid}-时间轴.wav"
        effect = assets / f"{sid}-音效.wav"
        source_args = ["-loop", "1"] if s["type"] == "concept_card" else ["-ss", s.get("retry_in", s.get("in", 0)) if attempt else s.get("in", 0)]
        backdrop = s.get("backdrop", plan.get("backdrop"))
        mat = "0xF1F3FA" if backdrop == "editorial_light" else "0x142238"
        if s["motion"] == "focus":
            scale = "scale=804:990:force_original_aspect_ratio=increase,crop=804:990"
        else:
            scale = "scale=804:990:force_original_aspect_ratio=decrease"
        effect_spec = s.get("click_event")
        if s["motion"] == "push":
            lead = effect_spec["frame"] if effect_spec else 0
            scale = ("scale=804:990:force_original_aspect_ratio=decrease,"
                     f"pad=804:990:(ow-iw)/2:(oh-ih)/2:color={mat},scale=1608:1980,"
                     f"zoompan=z='1+0.065*min(1,max(0,(on-{lead})/12))':"
                     "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=804x990:fps=30")
        fit = f"fps=30,setsar=1,{scale},pad=1080:1920:(76+(804-iw)/2):(325+(990-ih)/2):color={mat}"
        palette = {"dip": "0x142238", "light_dip": "0xEFF1FA"}
        fade = f",fade=t=in:st=0:d=0.10:color={palette[s['transition']]}" if s["transition"] in palette else ""
        graph = f"[0:v]{fit}{fade}[b];[b][1:v]overlay=0:0"
        extra = []
        if effect_spec:
            k, x, y = (effect_spec[key] for key in ("frame", "x", "y"))
            extra = ["-i", assets / "cursor.png"]
            graph += (f",drawbox=x={x-26}:y={y-26}:w=52:h=52:color=0xB4BFFF:t=4:enable='between(n,{k},{k+8})'[mark];"
                      "[2:v]crop=50:60:0:0[p];"
                      f"[mark][p]overlay=x='{x}+68*max(0,({k}-n)/8)':"
                      f"y='{y}+30*max(0,({k}-n)/8)':enable='between(n,{k-8},{k+10})'")
        ff(*source_args, "-i", s["source"], "-i", assets / f"{sid}-header.png", *extra, "-an",
           "-filter_complex", graph + ",format=yuv420p",
           "-frames:v", n, "-c:v", "libx264", "-preset", "ultrafast", "-crf", 18, clip)
        ff("-i", clip, "-i", assets / f"{sid}-caption.png", "-an",
           "-filter_complex", "overlay=0:0,format=yuv420p",
           "-frames:v", n, "-c:v", "libx264", "-preset", "ultrafast", "-crf", 18, boxed)
        ff("-i", s["voice_file"], "-af", "apad", "-t", duration, voice)
        if effect_spec:
            delay = effect_spec["frame"] * 1600
            ff("-f", "lavfi", "-i", "sine=frequency=940:sample_rate=48000:duration=0.06",
               "-af", f"volume=0.22,afade=t=out:st=0.006:d=0.054,adelay={delay}S,apad",
               "-t", duration, effect)
        elif s["sound"] == "tick":
            ff("-f", "lavfi", "-i", "sine=frequency=880:sample_rate=48000:duration=0.10",
               "-af", "volume=0.18,afade=t=out:st=0.02:d=0.08,apad", "-t", duration, effect)
        else:
            ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", duration, effect)
        raw.append(clip)
        styled.append(boxed)
        voices.append(voice)
        effects.append(effect)
    concat(raw, assets / "无字幕画面.mp4", assets)
    concat(styled, assets / "合成画面.mp4", assets)
    concat(voices, assets / "口播.wav", assets)
    concat(effects, assets / "音效.wav", assets)
    voice_mean, _ = db(assets / "口播.wav")
    process_mix(plan, out, shots[-1]["end"], voice_mean, attempt)
    ff("-i", assets / "合成画面.mp4", "-i", assets / "混音.wav",
       "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
       "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", out / "待验收.mp4")
    write_json(out / "音画时间轴.json", shots)
    write_subtitles(shots, assets / "字幕.srt")
    return out / "待验收.mp4"


def process_mix(plan, out, duration, voice_mean, attempt):
    assets = out / "素材"
    music = plan.get("music")
    if music:
        gain = min(0, voice_mean - (21 if attempt else 17) - db(music)[0])
        ff("-stream_loop", "-1", "-i", music, "-af",
           f"aresample=48000,aformat=channel_layouts=mono,volume={gain}dB,afade=t=out:st={duration-.33}:d=0.33",
           "-t", duration, assets / "音乐.wav")
    else:
        ff("-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", duration, assets / "音乐.wav")
    ff("-i", assets / "音乐.wav", "-i", assets / "音效.wav",
       "-filter_complex", "amix=inputs=2:normalize=0", assets / "配乐音效.wav")
    ff("-i", assets / "口播.wav", "-i", assets / "配乐音效.wav",
       "-filter_complex", "amix=inputs=2:normalize=0,alimiter=limit=0.82:level=0,volume=-1dB", assets / "混音.wav")


def write_subtitles(shots, output):
    def stamp(t):
        milliseconds = round(t * 1000)
        s, ms = divmod(milliseconds, 1000)
        m, s = divmod(s, 60)
        h, m = divmod(m, 60)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    output.write_text("\n".join(
        f"{i}\n{stamp(s['start'])} --> {stamp(s['end'])}\n"
        + "\n".join(s["rendered_caption"]) + "\n" for i, s in enumerate(shots, 1)
    ))


def frames_at(path, rate):
    return command("ffmpeg", "-nostdin", "-v", "error", "-i", path,
                   "-vf", f"fps={rate},scale=108:192,format=rgb24",
                   "-f", "rawvideo", "-", binary=True)


def visual_metrics(path, shots):
    raw = frames_at(path, 6)
    size = 108 * 192 * 3
    previous, still, dark = {}, {}, {}
    caption_evidence = {}
    for offset in range(0, len(raw), size):
        t = (offset // size + 0.5) / 6
        shot = next((s for s in shots if s["start"] <= t < s["end"]), shots[-1])
        sid = shot["id"]
        frame = raw[offset:offset+size]
        region = bytes(frame[(y*108+x)*3+k] for y in range(36,129,2)
                       for x in range(9,86,2) for k in range(3))
        if sid in previous:
            change = sum(abs(a-b) for a,b in zip(region, previous[sid])) / len(region)
            run = still.setdefault(sid, [0, 0])
            run[0] = run[0]+1 if change < 0.95 else 0
            run[1] = max(run)
        previous[sid] = region
        if max(region) < 48 or max(region)-min(region) < 15:
            dark[sid] = dark.get(sid, 0)+1
        # Inspect decoded pixels of the opaque caption plate and rendered glyphs.
        samples = [frame[(y*108+x)*3:(y*108+x)*3+3]
                   for y in range(140,159) for x in range(11,84)]
        by, bx = (146, 48) if shot.get("caption_style") == "capsule" else (158, 85)
        background = frame[(by*108+bx)*3:(by*108+bx)*3+3]
        def luminance(pixel):
            values = [v/255 / 12.92 if v/255 <= .04045 else ((v/255+.055)/1.055)**2.4 for v in pixel]
            return sum(c*v for c,v in zip((.2126,.7152,.0722),values))
        bright = sum(min(pixel) >= 195 for pixel in samples)
        ratio = (luminance(max(samples, key=luminance))+.05)/(luminance(background)+.05)
        max_bright, min_ratio = caption_evidence.get(sid, (100000, 100))
        caption_evidence[sid] = (min(max_bright, bright), min(min_ratio, ratio))
    return ({sid: round(run[1]/6, 2) for sid, run in still.items()}, dark,
            {sid: {"白字像素至少": bright, "对比度至少": round(ratio, 2)}
             for sid,(bright,ratio) in caption_evidence.items()})


def check(plan, shots, video, out):
    assets = out / "素材"
    report = {}
    def row(key, ok, evidence):
        report[key] = {"passed": bool(ok), "evidence": evidence}
    info = media(video)
    duration = float(info["format"]["duration"])
    decoded = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-xerror", "-i", str(video),
                              "-map", "0:v", "-map", "0:a", "-f", "null", "-"],
                             capture_output=True)
    streams = {s["codec_type"]: s for s in info["streams"]}
    v = streams["video"]
    row("播放和完整解码", decoded.returncode == 0 and (v["width"],v["height"]) == (1080,1920)
        and "audio" in streams and info["format"]["tags"]["major_brand"] != "qt  ",
        {"video": v["codec_name"], "audio": streams.get("audio", {}).get("codec_name"),
         "尺寸": [v["width"],v["height"]], "ffmpeg_exit": decoded.returncode})
    voice = assets / "口播.wav"
    voice_duration = float(media(voice)["format"]["duration"])
    max_tail = duration - (shots[-1]["start"]+shots[-1]["voice_duration"])
    low, high = plan["duration_range"]
    row("成片和配音时长", low <= duration <= high and abs(duration-voice_duration) <= .12,
        {"视频": duration, "口播轨": voice_duration, "目标区间": [low,high]})
    quiet_voice, quiet_mix = silence(voice), silence(video)
    row("长时间静音", not quiet_voice and not quiet_mix,
        {"阈值": "-42 dB / 0.8 秒", "口播": quiet_voice, "成片": quiet_mix})
    x,y,w,h = CAPTION
    sx,sy,sw,sh = SAFE
    geometry = x >= sx and y >= sy and x+w <= sx+sw and y+h <= sy+sh and y >= VISUAL[1]+VISUAL[3]
    row("字幕安全区和避让", geometry, {"字幕框": CAPTION, "画面框": VISUAL, "安全框": SAFE,
        "方法": "渲染器将素材限定在独立画面区；文字绘制前实测宽度，越界中止"})
    still, dark, contrast = visual_metrics(video, shots)
    row("字幕对比度", len(contrast)==len(shots) and all(
        d["白字像素至少"] >= 2 and d["对比度至少"] >= 4.5 for d in contrast.values()), contrast)
    failures = {s["id"]: still.get(s["id"], 0) for s in shots
                if s["type"] not in {"concept_card","legacy_example"} and still.get(s["id"],0) >= 1.8}
    row("画面静止", not failures, {"每镜最长近静止_秒": still, "需返工": failures,
        "例外": "解释卡和旧版反例分别限四秒且合计不超过四分之一"})
    row("黑屏空画面素材缺失", not any(n >= 2 for n in dark.values()) and all(
        Path(s["source"]).is_file() for s in shots), {"各镜黑暗或低动态范围抽样数": dark, "帧抽样率": 6})
    voice_db, _ = db(voice)
    bed_db, bed_peak = db(assets / "配乐音效.wav")
    _, mix_peak = db(video)
    row("人声音效和音乐", bed_db <= voice_db-12 and bed_peak <= -24 and mix_peak <= -0.5,
        {"口播平均_dBFS":voice_db,"配乐音效平均_dBFS":bed_db,"配乐音效峰值_dBFS":bed_peak,"成片峰值_dBFS":mix_peak,
         "待听审": "响度和峰值仅做客观筛查，风格、人声自然度和遮蔽感需听审"})
    row("结尾完整", shots[-1].get("ending") is True and .03 <= max_tail <= .65 and
        abs(duration-shots[-1]["end"]) <= .12, {"尾部留白秒": round(max_tail,3), "有明确收束":shots[-1].get("ending",False)})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--allow-local-preview", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for name in ("自动验收.mp4", "待验收.mp4"):
        (out / name).unlink(missing_ok=True)
    attempts = []
    try:
        plan = json.loads(args.plan.read_text())
        if plan.get("voice_mode") == "local_preview" and not args.allow_local_preview:
            raise ValueError("本地占位配音仅用于明确启用的内部画面预览")
        root = args.plan.resolve().parent
        if plan.get("music"):
            plan["music"] = str((root / plan["music"]).resolve(strict=True))
        shots = timeline(plan, root, out)
        for shot in shots:
            shot["caption_style"] = plan.get("caption_style")
        for attempt in range(2):
            try:
                video = render(plan, shots, out, attempt)
                checks = check(plan, shots, video, out)
            except ValueError as error:
                checks = {"制作或检查异常": {"passed":False,"evidence":str(error)}}
            attempts.append({"attempt":attempt+1, "checks":checks})
            if all(item["passed"] for item in checks.values()):
                final = out / "自动验收.mp4"
                with video.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                report = {"passed":True,"engine":"FFmpeg","voice_mode":plan.get("voice_mode","jianying_free"),"voice_evidence":plan.get("voice_evidence"),"attempts":attempts,"sha256":digest}
                video.replace(final)
                write_json(out / "自动质检.json", report)
                return 0
    except (ValueError, FileNotFoundError, KeyError) as error:
        attempts.append({"attempt":1,"checks":{"素材或方案": {"passed":False,"evidence":str(error)}}})
    write_json(out / "自动质检.json", {"passed":False,"engine":"FFmpeg","attempts":attempts})
    return 1


if __name__ == "__main__":
    sys.exit(main())
