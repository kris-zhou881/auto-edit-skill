#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { createReadStream } from 'node:fs';
import { mkdir, readdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';

function run(program, args) {
  const result = spawnSync(program, args, { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
  if (result.error) throw result.error;
  if (result.status !== 0) throw new Error(result.stderr.trim() || `${program} 未完成`);
  return result;
}

function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}

async function inspect(timeline, video, output) {
  const { assets, shots } = JSON.parse(await readFile(timeline, 'utf8'));
  requireValue(Array.isArray(assets) && Array.isArray(shots) && shots.length, '时间线需要 assets 和非空 shots');
  const sourceTypes = new Set(['code', 'terminal', 'ui', 'architecture', 'docs', 'photo']);
  const origins = new Set(['capture', 'trace_replay', 'animation', 'generated']);
  const sources = new Map();
  for (const source of assets) {
    requireValue(typeof source?.id === 'string' && source.id && !sources.has(source.id), '素材 ID 为空或重复');
    requireValue(sourceTypes.has(source.type) && origins.has(source.origin), `${source.id} 的素材类型或来源无效`);
    requireValue(['available', 'missing'].includes(source.availability), `${source.id} 的可用状态无效`);
    if (source.availability === 'available') {
      requireValue(typeof source.source === 'string' && source.source.trim(), `${source.id} 缺证据来源`);
      requireValue(typeof source.local_path === 'string' && source.local_path.trim(), `${source.id} 缺本地路径`);
      requireValue((await stat(resolve(dirname(timeline), source.local_path))).isFile(), `${source.id} 的本地路径应为文件`);
    }
    if (source.type === 'photo' && source.origin === 'capture' && source.availability === 'available') {
      requireValue([source.source_identity, source.author, source.rights]
        .every(value => typeof value === 'string' && value.trim()), `${source.id} 缺照片身份、作者或许可`);
    }
    sources.set(source.id, source);
  }

  const probe = JSON.parse(run('ffprobe', ['-v', 'error', '-select_streams', 'v:0',
    '-show_entries', 'stream=duration:format=duration', '-of', 'json', video]).stdout);
  const duration = [probe.streams?.[0]?.duration, probe.format?.duration]
    .map(Number).find(value => Number.isFinite(value) && value > 0);
  requireValue(probe.streams?.length && Number.isFinite(duration) && duration > 0, '媒体没有可读的视频时长');
  const issues = [];
  const frames = [];
  const report = (layer, start, end, status, evidence, fix) => issues.push({ layer, start, end, status, evidence, fix });
  let cursor = 0;
  let realSeconds = 0;
  const seenPhotos = new Set();
  for (const [index, shot] of shots.entries()) {
    const source = sources.get(shot?.asset_id);
    requireValue(source && sourceTypes.has(shot.type), `镜头 ${index + 1} 的素材引用或类型无效`);
    const { start, end } = shot;
    requireValue(Number.isFinite(start) && Number.isFinite(end) && end > start
      && Math.abs(start - cursor) < 0.000001, `镜头 ${index + 1} 必须从 ${cursor} 秒连续开始`);
    cursor = end;
    const length = end - start;
    if (source.availability === 'missing') {
      report('素材', start, end, 'failed', `缺少 ${source.id}`, '补录主张所需证据，或缩小主张范围。');
    } else if (source.origin === 'capture') {
      if (source.type === 'photo') {
        const identity = source.source_identity.trim();
        if (seenPhotos.has(identity)) {
          report('素材', start, end, 'failed', `照片重复使用：${identity}`, '用另一张有来源的照片，或合成同一个连续镜头。');
        }
        seenPhotos.add(identity);
      }
      realSeconds += length;
    }
    const changes = shot.visual_changes ?? [];
    requireValue(Array.isArray(changes) && changes.every((change, i) => change
      && Number.isFinite(change.at) && change.at >= start && change.at < end
      && (i === 0 || change.at > changes[i - 1].at)
      && typeof change.kind === 'string'), `镜头 ${index + 1} 的动效时间点无效`);
    const highlights = [];
    let previousTarget;
    for (const change of changes) {
      if (change.kind !== 'line_highlight' || typeof change.target !== 'string') continue;
      const target = change.target.trim();
      if (!target || target === previousTarget) continue;
      highlights.push(change.at);
      previousTarget = target;
    }
    const boundaries = [start, ...highlights, end];
    const readableCode = shot.type === 'code' && highlights.length >= 2
      && boundaries.slice(1).every((next, i) => next - boundaries[i] <= 6.000001);
    if (length > 10.000001 || (length > 6.000001 && !readableCode)) {
      report('节奏', start, end, 'failed', length > 10 ? '镜头超过 10 秒' : '超过 6 秒且未满足代码高亮例外',
        '切换有效视角，或在 10 秒内按多个关键行设置连续高亮。');
    }
  }
  const denominator = Math.max(cursor, duration);
  const ratio = realSeconds / denominator;
  if (realSeconds <= denominator / 2 + 0.000001) report('素材', 0, duration, 'failed', `真实素材占比 ${(ratio * 100).toFixed(2)}%`, '用可追溯的真实照片、截图或录屏替换缺证据的主镜头，使成片真实占比超过 50%。');
  if (Math.abs(cursor - duration) > 0.08) report('节奏', Math.min(cursor, duration), Math.max(cursor, duration),
    'failed', '时间线与视频时长不同', '更新为实际导出版本的逐镜边界，再重新质检。');

  await mkdir(output);
  const detected = run('ffmpeg', ['-hide_banner', '-nostats', '-loglevel', 'info', '-xerror',
    '-i', video, '-an', '-vf', 'blackdetect=d=0.2:pic_th=0.98:pix_th=0.10,freezedetect=n=-60dB:d=1.5',
    '-f', 'null', '-']).stderr;
  for (const match of detected.matchAll(/black_start:([\d.]+)\s+black_end:([\d.]+)/g)) {
    report('黑屏/空白', Number(match[1]), Number(match[2]), 'needs_review', '疑似黑屏', '回看片段，剪掉多余黑屏，保留仍可读的深色界面。');
  }
  let frozenAt;
  for (const match of detected.matchAll(/lavfi\.freezedetect\.freeze_(start|end):\s*([\d.]+)/g)) {
    if (match[1] === 'start') frozenAt = Number(match[2]);
    else if (frozenAt !== undefined) {
      report('黑屏/空白', frozenAt, Number(match[2]), 'needs_review', '疑似冻结', '回看是否有可读信息或故意停顿，必要时缩短或移动高亮。');
      frozenAt = undefined;
    }
  }
  if (frozenAt !== undefined) report('黑屏/空白', frozenAt, duration, 'needs_review', '疑似冻结至片尾', '回看结尾，必要时删掉无信息停顿。');

  const frameDirectory = join(output, 'frames');
  await mkdir(frameDirectory);
  run('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-xerror', '-i', video, '-an',
    '-vf', 'fps=1:start_time=0:round=up:eof_action=pass', '-q:v', '2', '-start_number', '0',
    join(frameDirectory, '%05d.jpg')]);
  for (const file of (await readdir(frameDirectory)).sort()) {
    frames.push({ second: Number(file.slice(0, -4)), file: `frames/${file}`, status: 'pending_visual_review' });
  }
  requireValue(frames.length === Math.ceil(duration), '逐秒帧数量与视频时长不符');
  const hash = createHash('sha256');
  for await (const chunk of createReadStream(video)) hash.update(chunk);
  const result = {
    video, video_sha256: hash.digest('hex'), duration, real_seconds: realSeconds, real_ratio: ratio,
    machine_status: issues.some(issue => issue.status === 'failed') ? 'failed' : 'needs_review',
    issues: issues.sort((a, b) => a.start - b.start), frames,
    manual_review: ['逐帧可读性和脱敏', '完整连看连听', '代码、命令与架构准确性', '核心功能覆盖'],
  };
  await writeFile(join(output, 'machine-qa.json'), JSON.stringify(result, null, 2) + '\n');
  process.exitCode = result.machine_status === 'failed' ? 1 : 0;
}

const args = process.argv.slice(2);
if (args.includes('--help')) {
  console.log('用法：node scripts/inspect_technical.mjs <时间线 JSON> <视频> <新的质检目录>');
} else if (args.length !== 3) {
  console.error('需要三个参数，使用 --help 查看用法。');
  process.exitCode = 2;
} else {
  await inspect(...args).catch(error => {
    console.error(error.message);
    process.exitCode = 2;
  });
}
