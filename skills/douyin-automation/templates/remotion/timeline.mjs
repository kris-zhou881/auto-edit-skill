const integer = (value, min, max) => Number.isInteger(value) && value >= min && value <= max;
const label = value => typeof value === 'string' && value.trim().length > 0;
const inRange = (value, min, max) => Number.isFinite(value) && value >= min && value <= max;
const localFile = value => label(value) && !/[:\\?#%]/.test(value)
  && value.split('/').every(part => part && part !== '..' && part !== '.');

function check(condition, message) {
  if (!condition) throw new Error(`动画时间轴：${message}`);
}

export function validateTimeline(timeline) {
  const {fps, duration, shots, captions, audio} = timeline;
  check(integer(fps, 24, 60) && integer(duration, 1, Number.MAX_SAFE_INTEGER), '帧率或总帧数无效');
  check(Array.isArray(shots) && shots.length && Array.isArray(captions) && Array.isArray(audio), '缺少镜头、字幕或音轨数组');
  const interval = ({from, to}) => integer(from, 0, duration - 1) && integer(to, from + 1, duration);
  let end = 0;
  shots.forEach((shot, index) => {
    const {from, to, type, title, source, camera, transition = 0} = shot;
    const where = `第 ${index + 1} 镜`;
    check(interval(shot) && from === end, `${where}有重叠或断帧`);
    check(label(title) && label(source), `${where}缺标题或来源`);
    check(transition === 0 || (index > 0 && integer(transition, 2, Math.min(fps, to - from - 1))), `${where}转场帧数无效`);
    if (camera) {
      check(integer(camera.from, from, to - 2) && integer(camera.to, camera.from + 1, to - 1)
        && inRange(camera.x, -180, 180) && inRange(camera.y, -240, 240)
        && inRange(camera.scale, 1, 1.35), `${where}镜头运动超出范围`);
    }
    if (type === 'code') {
      check(label(shot.fileLabel) && Array.isArray(shot.lines) && shot.lines.length, `${where}缺代码内容`);
      if (shot.readout) {
        const {at, values} = shot.readout;
        check(integer(at, from, to - 1) && Array.isArray(values) && values.length > 0
          && values.length <= 4 && values.every(label), `${where}结果读数无效`);
      }
      let prior = from - 1;
      shot.lines.forEach(line => {
        check(integer(line.at, prior + 1, to - 1) && typeof line.text === 'string', `${where}代码行必须按帧排序`);
        prior = line.at;
      });
    } else if (type === 'flow') {
      check(Array.isArray(shot.nodes) && shot.nodes.length >= 2 &&
        shot.nodes.length <= 8, `${where}流程图需有 2–8 个节点`);
      const ids = new Set();
      for (const node of shot.nodes ?? []) {
        check(label(node.id) && !ids.has(node.id) && label(node.label) &&
          inRange(node.x, 110, 690) && inRange(node.y, 80, 610) &&
          integer(node.at, from, to - 1), `${where}流程节点无效`);
        ids.add(node.id);
      }
      check(Array.isArray(shot.edges), `${where}流程关系缺失`);
      for (const edge of shot.edges ?? []) {
        check(ids.has(edge.from) && ids.has(edge.to) && edge.from !== edge.to &&
          integer(edge.at, from, to - 1), `${where}流程连线无效`);
      }
    } else {
      check(['image', 'video'].includes(type) && localFile(shot.file), `${where}素材类型或路径无效`);
      if (type === 'video') check(integer(shot.sourceStart ?? 0, 0, Number.MAX_SAFE_INTEGER), `${where}录屏入点无效`);
    }
    end = to;
  });
  check(end === duration, '最后一镜必须覆盖至片尾');

  end = 0;
  captions.forEach(caption => {
    check(interval(caption) && caption.from >= end && label(caption.text), '字幕必须有文字且按帧排列');
    check(caption.emphasis === undefined || (label(caption.emphasis) && caption.text.includes(caption.emphasis)
      && integer(caption.emphasisAt, caption.from, caption.to - 1)), '字幕强调词及时间无效');
    check(caption.style === undefined || ['kinetic', 'sticker', 'minimal'].includes(caption.style),
      '字幕花字样式无效');
    if (caption.segments !== undefined) {
      check(Array.isArray(caption.segments) && caption.segments.length > 0 &&
        caption.segments.length <= 16, '花字字幕分段需有 1–16 项');
      check(caption.segments.every(segment =>
        label(segment.text) && integer(segment.at, caption.from, caption.to - 1) &&
        (segment.tone === undefined || ['normal', 'accent', 'alert'].includes(segment.tone)) &&
        (segment.emphasisAt === undefined ||
          integer(segment.emphasisAt, segment.at, caption.to - 1))), '花字分段时间或强调状态无效');
      check(caption.segments.map(segment => segment.text).join('') === caption.text,
        '花字分段合并文字必须与字幕一致');
      check(caption.segments.every((segment, idx) =>
        idx === 0 || segment.at >= caption.segments[idx - 1].at), '花字分段 cue 必须单调');
    }
    end = caption.to;
  });
  audio.forEach(track => {
    check(interval(track) && localFile(track.file), '音频区间或本地路径无效');
    check(['voice', 'music', 'sfx'].includes(track.role) && inRange(track.gain, 0, 1), '音轨类别或增益无效');
  });
  return timeline;
}
