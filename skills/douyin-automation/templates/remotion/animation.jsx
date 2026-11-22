import React from 'react';
import {AbsoluteFill, Composition, Easing, Img, OffthreadVideo, Sequence, interpolate,
  registerRoot, staticFile, useCurrentFrame} from 'remotion';
import {Audio} from '@remotion/media';
import timeline from './motion-timeline.json';
import {validateTimeline} from './timeline.mjs';

const {fps, duration, shots, captions, audio} = validateTimeline(timeline);
const theme = {
  background: '#161c22',
  paper: '#f5eee0',
  ink: '#192125',
  muted: '#586059',
  accent: '#b94529',
  highlight: '#f0d6c0',
  white: '#fff8ec',
  line: '#ddd2c0',
  shadow: '#10161966',
  sans: '"PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", sans-serif',
  mono: '"SF Mono", Menlo, Consolas, monospace',
};
const ease = (frame, start, end) => interpolate(frame, [start, end], [0, 1], {
  extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic),
});

function Code({shot, frame}) {
  const visible = shot.lines.filter(line => frame >= line.at);
  return (
    <div style={{background: theme.paper, color: theme.ink, borderRadius: 18, overflow: 'hidden',
      boxShadow: `0 28px 55px ${theme.shadow}`, fontFamily: theme.mono}}>
      <div style={{padding: '24px 32px', borderBottom: `2px solid ${theme.line}`, fontSize: 28, color: theme.muted}}>
        {shot.fileLabel}
      </div>
      <div style={{padding: '34px 28px', minHeight: 370}}>
        {visible.map(({at, text}, index) => {
          const active = index === visible.length - 1;
          const progress = ease(frame, at, at + Math.max(2, Math.round(fps * 0.16)));
          return <div key={at} style={{fontSize: 37, lineHeight: 1.48, padding: '4px 10px',
            background: active ? theme.highlight : undefined, opacity: 0.55 + 0.45 * progress,
            transform: `translateY(${(1 - progress) * 13}px)`, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere'}}>
            {text}
          </div>;
        })}
      </div>
    </div>
  );
}

function Readout({values, at, frame}) {
  return <div style={{display: 'flex', gap: 30, marginTop: 50, paddingTop: 22,
    borderTop: `2px solid ${theme.muted}`, fontFamily: theme.mono}}>
    {values.map((value, index) => {
      const start = at + index * Math.round(fps * 0.095);
      const progress = ease(frame, start, start + Math.round(fps * 0.22));
      return <div key={index} style={{opacity: progress, transform: `translateY(${(1 - progress) * 24}px)`,
        fontSize: 92, fontWeight: 700, flex: 1, maxWidth: 225, overflowWrap: 'anywhere'}}>{value}</div>;
    })}
  </div>;
}

function Shot({shot, frame, frozen = false}) {
  const {camera} = shot;
  const progress = camera ? ease(frame, camera.from, camera.to) : 0;
  const footageFrame = (shot.sourceStart ?? 0) + frame - shot.from;
  return <AbsoluteFill style={{background: theme.background, color: theme.white, fontFamily: theme.sans}}>
    <div style={{position: 'absolute', left: 88, right: 145, top: 410}}>
      <div style={{fontSize: 64, lineHeight: 1.15, fontWeight: 760, marginBottom: 40}}>{shot.title}</div>
      <div style={{borderRadius: 18, overflow: 'hidden'}}>
        <div style={{transform: camera ? `translate(${camera.x * progress}px, ${camera.y * progress}px)
          scale(${1 + (camera.scale - 1) * progress})` : undefined}}>
          {shot.type === 'code' ? <Code shot={shot} frame={frame} /> : (
            <div style={{position: 'relative', height: 690}}>
              {shot.type === 'image'
                ? <Img src={staticFile(shot.file)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
                : <OffthreadVideo src={staticFile(shot.file)} trimBefore={shot.sourceStart ?? 0}
                    {...(frozen ? {trimBefore: footageFrame, trimAfter: footageFrame + 1} : {})}
                    muted style={{width: '100%', height: '100%', objectFit: 'contain'}} />}
            </div>
          )}
        </div>
      </div>
      <div style={{marginTop: 28, fontSize: 25, color: theme.white, lineHeight: 1.4}}>{shot.source}</div>
      {shot.readout && frame >= shot.readout.at && <Readout {...shot.readout} frame={frame} />}
    </div>
  </AbsoluteFill>;
}

function Caption({caption, frame}) {
  const {text, emphasis, emphasisAt} = caption;
  const start = emphasis && frame >= emphasisAt ? text.indexOf(emphasis) : -1;
  return <div style={{position: 'absolute', left: 88, right: 150, bottom: 350, padding: '17px 28px',
    borderRadius: 14, background: theme.paper, color: theme.ink, fontFamily: theme.sans,
    fontSize: 45, fontWeight: 700, textAlign: 'center', lineHeight: 1.35}}>
    {start < 0 ? text : <>
      {text.slice(0, start)}<span style={{color: theme.accent}}>{emphasis}</span>{text.slice(start + emphasis.length)}
    </>}
  </div>;
}

function Timeline({preview}) {
  const frame = useCurrentFrame();
  const index = shots.findIndex(shot => frame >= shot.from && frame < shot.to);
  const shot = shots[index];
  const previous = shots[index - 1];
  const wiping = previous && frame < shot.from + (shot.transition ?? 0);
  const progress = wiping ? ease(frame, shot.from, shot.from + shot.transition - 1) : 1;
  const caption = preview && captions.find(({from, to}) => frame >= from && frame < to);
  return <AbsoluteFill>
    {wiping && previous.type === 'video' &&
      <Sequence from={frame} durationInFrames={1}><Shot shot={previous} frame={previous.to - 1} frozen /></Sequence>}
    {wiping && previous.type !== 'video' && <Shot shot={previous} frame={previous.to - 1} />}
    <AbsoluteFill style={{clipPath: wiping ? `inset(0 ${(1 - progress) * 100}% 0 0)` : undefined}}>
      <Sequence from={shot.from} durationInFrames={shot.to - shot.from}><Shot shot={shot} frame={frame} /></Sequence>
    </AbsoluteFill>
    {caption && <Caption caption={caption} frame={frame} />}
    {preview && audio.map(({from, to, file, gain}, index) => (
      <Sequence key={index} from={from} durationInFrames={to - from}>
        <Audio src={staticFile(file)} volume={gain} />
      </Sequence>
    ))}
  </AbsoluteFill>;
}

function Root() {
  return ['Preview', 'Picture'].map(id => <Composition key={id} id={id} component={Timeline}
    defaultProps={{preview: id === 'Preview'}} width={1080} height={1920} fps={fps} durationInFrames={duration} />);
}

registerRoot(Root);
