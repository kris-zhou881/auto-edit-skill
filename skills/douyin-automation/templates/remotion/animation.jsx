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

function Flow({shot, frame}) {
  const nodes = shot.nodes ?? [];
  const edges = shot.edges ?? [];
  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
  return <div style={{height: 690, position: 'relative', background: '#202a32', borderRadius: 18,
    overflow: 'hidden', border: '2px solid #354451'}}>
    <svg width="100%" height="100%" viewBox="0 0 800 690" style={{position: 'absolute', inset: 0}}>
      {edges.map((edge, i) => {
        const a = byId[edge.from], b = byId[edge.to];
        if (!a || !b) return null;
        const p = ease(frame, edge.at, edge.at + Math.round(fps * 0.36));
        const ex = a.x + (b.x - a.x) * p, ey = a.y + (b.y - a.y) * p;
        const phase = p > 0 ? ((frame - edge.at) % Math.max(1, fps)) / Math.max(1, fps) : 0;
        return <g key={i}>
          <line x1={a.x} y1={a.y} x2={ex} y2={ey} stroke="#efb979" strokeWidth="5" strokeLinecap="round" />
          {p > 0 && <circle cx={a.x + (ex-a.x)*phase} cy={a.y + (ey-a.y)*phase}
            r="8" fill="#fff1d0" />}
        </g>;
      })}
    </svg>
    {nodes.map(node => {
      const p = ease(frame, node.at, node.at + Math.round(fps * 0.25));
      return <div key={node.id} style={{position: 'absolute',
        left: `calc(${node.x / 800 * 100}% - 96px)`,
        top: `calc(${node.y / 690 * 100}% - 37px)`,
        width: 192, minHeight: 74, borderRadius: 16, background: '#30434c',
        border: '2px solid #9bc9bc', color: '#fff8ec',
        opacity: p, transform: `scale(${0.8 + .2*p})`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        textAlign: 'center', fontSize: 26, fontWeight: 730, padding: 9}}>
        {node.label}
      </div>;
    })}
  </div>;
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
          {shot.type === 'code' ? <Code shot={shot} frame={frame} /> :
           shot.type === 'flow' ? <Flow shot={shot} frame={frame} /> : (
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

// Remotion-drawn motion typography. Does not invoke macOS subtitle/overlay APIs.
const captionPalettes = {
  kinetic: {normal: '#FFF8EC', accent: '#FFE16A', alert: '#FF9777', outline: '#172532'},
  sticker: {normal: '#FFFFFF', accent: '#FFDD55', alert: '#FF8888', outline: '#162330'},
  minimal: {normal: '#FFFFFF', accent: '#C7F5AB', alert: '#FFD09B', outline: '#12212B'},
};

function Caption({caption, frame}) {
  const {text, emphasis, emphasisAt} = caption;
  const styleName = caption.style ?? 'kinetic';
  const palette = captionPalettes[styleName] ?? captionPalettes.kinetic;
  const startIndex = emphasis ? text.indexOf(emphasis) : -1;
  // Old timelines still get animated entrance and a timed keyword punch.
  const pieces = caption.segments ?? (startIndex < 0 ? [{text, at: caption.from}] : [
    ...(startIndex ? [{text: text.slice(0, startIndex), at: caption.from}] : []),
    {text: emphasis, at: caption.from, tone: 'accent', emphasisAt},
    ...(startIndex + emphasis.length < text.length ?
      [{text: text.slice(startIndex + emphasis.length), at: caption.from}] : []),
  ]);
  const inFrames = Math.max(4, Math.round(fps * 0.22));
  const enter = ease(frame, caption.from, caption.from + inFrames);
  const endStart = Math.max(caption.from, caption.to - Math.round(fps * 0.16));
  const exit = 1 - ease(frame, endStart, caption.to);
  return <div style={{
    position: 'absolute', left: 88, right: 192, bottom: 445,
    pointerEvents: 'none', textAlign: 'center',
    transform: 'translateY(' + ((1 - enter) * 19) + 'px)',
    opacity: enter * exit, fontFamily: theme.sans,
  }}>
    <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'center',
      alignItems: 'baseline', gap: '0 2px',
      padding: styleName === 'sticker' ? '16px 20px' : '8px 14px',
      borderRadius: 20,
      background: styleName === 'sticker' ? 'rgba(11,24,33,0.66)' : 'transparent',
    }}>
      {pieces.map((piece, i) => {
        const cue = piece.emphasisAt ?? piece.at;
        const progress = ease(frame, piece.at, piece.at + inFrames);
        const highlighted = (piece.tone === 'accent' || piece.tone === 'alert') && frame >= cue;
        const pulse = highlighted ? 1 - ease(frame, cue, cue + Math.round(fps * 0.25)) : 0;
        const size = styleName === 'minimal' ? 49 : styleName === 'sticker' ? 55 : 57;
        const color = highlighted ? palette[piece.tone] : palette.normal;
        return <span key={i} style={{position: 'relative', display: 'inline-block',
          whiteSpace: 'pre-wrap', opacity: progress,
          transform: 'translateY(' + ((1 - progress) * 22) + 'px) scale(' +
            (0.88 + 0.12 * progress + (highlighted ? 0.10 * pulse : 0)) + ')',
          fontSize: size, fontWeight: 900, letterSpacing: '0.5px', lineHeight: 1.24,
          color, WebkitTextStroke: (styleName === 'minimal' ? 1.3 : 2.0) + 'px ' + palette.outline,
          paintOrder: 'stroke fill',
          textShadow: '0 3px 0 #102330, 0 7px 16px rgba(0,0,0,0.6)',
        }}>
          <span style={{position: 'relative', zIndex: 1}}>{piece.text}</span>
          {highlighted && styleName !== 'minimal' &&
            <span aria-hidden="true" style={{position: 'absolute', left: 0, bottom: 3,
              height: 10, width: (87 * ease(frame, cue, cue + Math.round(fps * 0.22))) + '%',
              background: piece.tone === 'alert' ? '#F65E52' : '#F29A38',
              borderRadius: 8, opacity: 0.85}} />}
        </span>;
      })}
    </div>
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
