import {existsSync, readFileSync, writeFileSync} from 'node:fs';
import {validateTimeline} from './timeline.mjs';

const timeline = JSON.parse(readFileSync('motion-timeline.json', 'utf8'));
validateTimeline(timeline);

for (const item of [...timeline.shots, ...timeline.audio]) {
  if (item.file && !existsSync(`public/${item.file}`)) {
    throw new Error(`缺少项目素材 public/${item.file}`);
  }
}

function timestamp(frame) {
  const milliseconds = Math.round(1000 * frame / timeline.fps);
  return [Math.floor(milliseconds / 3600000), Math.floor(milliseconds / 60000) % 60,
    Math.floor(milliseconds / 1000) % 60].map(part => String(part).padStart(2, '0')).join(':')
    + ',' + String(milliseconds % 1000).padStart(3, '0');
}

const srt = timeline.captions.map(({from, to, text}, index) =>
  `${index + 1}\n${timestamp(from)} --> ${timestamp(to)}\n${text.trim()}\n`).join('\n');
writeFileSync(process.argv[2] ?? '字幕.srt', srt, {flag: 'wx'});
console.log(`已检查 ${timeline.shots.length} 个镜头，导出 ${timeline.captions.length} 条字幕（花字由 Remotion 视频内嵌生成，SRT 仅用于辅助编辑）。`);
