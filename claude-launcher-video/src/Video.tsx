import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
  Img,
  staticFile,
} from "remotion";

// ── Catppuccin Mocha palette ──
const bg = "#1e1e2e";
const accent = "#89b4fa";
const green = "#a6e3a1";
const yellow = "#f9e2af";
const red = "#f38ba8";
const mauve = "#cba6f7";
const txt = "#cdd6f4";
const sub = "#a6adc8";
const surface = "#313244";
const crust = "#11111b";

// ── SVG Components (built with svg-precision-skill) ──
const ReactAtom: React.FC<{ size?: number }> = ({ size = 200 }) => (
  <svg width={size} height={size} viewBox="0 0 200 200">
    <ellipse fill="none" stroke="#61dafb" strokeWidth="3" cx="100" cy="100" rx="80" ry="28" />
    <ellipse fill="none" stroke="#61dafb" strokeWidth="3" transform="rotate(60 100 100)" cx="100" cy="100" rx="80" ry="28" />
    <ellipse fill="none" stroke="#61dafb" strokeWidth="3" transform="rotate(120 100 100)" cx="100" cy="100" rx="80" ry="28" />
    <circle fill="#61dafb" cx="100" cy="100" r="10" />
  </svg>
);

const FilmIcon: React.FC<{ size?: number }> = ({ size = 120 }) => (
  <svg width={size} height={size} viewBox="0 0 120 120">
    <rect fill="none" stroke={mauve} strokeWidth="3" x="15" y="10" width="90" height="100" rx="8" ry="8" />
    <rect fill="none" stroke={mauve} strokeWidth="2" x="15" y="10" width="18" height="100" />
    <rect fill="none" stroke={mauve} strokeWidth="2" x="87" y="10" width="18" height="100" />
    <line stroke={mauve} strokeWidth="2" x1="15" y1="35" x2="33" y2="35" />
    <line stroke={mauve} strokeWidth="2" x1="15" y1="60" x2="33" y2="60" />
    <line stroke={mauve} strokeWidth="2" x1="15" y1="85" x2="33" y2="85" />
    <line stroke={mauve} strokeWidth="2" x1="87" y1="35" x2="105" y2="35" />
    <line stroke={mauve} strokeWidth="2" x1="87" y1="60" x2="105" y2="60" />
    <line stroke={mauve} strokeWidth="2" x1="87" y1="85" x2="105" y2="85" />
    <path fill={mauve} stroke="none" d="M50 45 L50 75 L72 60 Z" />
  </svg>
);

const CodeBracket: React.FC<{ size?: number }> = ({ size = 120 }) => (
  <svg width={size} height={size} viewBox="0 0 120 120">
    <path fill="none" stroke={accent} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" d="M45 25 L15 60 L45 95" />
    <path fill="none" stroke={accent} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" d="M75 25 L105 60 L75 95" />
    <line stroke={green} strokeWidth="3" strokeLinecap="round" x1="68" y1="20" x2="52" y2="100" />
  </svg>
);

// ── Animated particles background ──
const Particles: React.FC = () => {
  const frame = useCurrentFrame();
  const particles = Array.from({ length: 20 }, (_, i) => ({
    x: (i * 137.5) % 1920,
    y: (i * 97.3) % 1080,
    r: 2 + (i % 3),
    speed: 0.3 + (i % 5) * 0.15,
    opacity: 0.1 + (i % 4) * 0.05,
  }));

  return (
    <>
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: p.x,
            top: (p.y + frame * p.speed * 20) % 1120 - 40,
            width: p.r * 2,
            height: p.r * 2,
            borderRadius: "50%",
            background: accent,
            opacity: p.opacity,
          }}
        />
      ))}
    </>
  );
};

// ── SCENE 1: Title (0-90) ──
// "Remotion" title with React atom + Film icon, spring entrance
const TitleScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleScale = spring({ frame, fps, config: { damping: 12, mass: 0.8 } });
  const subtitleOp = interpolate(frame, [15, 35], [0, 1], { extrapolateRight: "clamp" });
  const subtitleY = interpolate(frame, [15, 35], [30, 0], { extrapolateRight: "clamp" });
  const iconOp = interpolate(frame, [5, 25], [0, 1], { extrapolateRight: "clamp" });
  const atomRotate = frame * 1.5;
  const lineWidth = interpolate(frame, [25, 50], [0, 600], { extrapolateRight: "clamp" });
  const tagOp = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const tagY = interpolate(frame, [40, 55], [20, 0], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg, justifyContent: "center", alignItems: "center" }}>
      <Particles />
      <div style={{ textAlign: "center", transform: `scale(${titleScale})`, zIndex: 1 }}>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 40, marginBottom: 30 }}>
          <div style={{ opacity: iconOp, transform: `rotate(${atomRotate}deg)` }}>
            <ReactAtom size={140} />
          </div>
          <div style={{ fontSize: 110, fontWeight: 900, color: txt, fontFamily: "system-ui, sans-serif", letterSpacing: -3 }}>
            Remot<span style={{ color: accent }}>ion</span>
          </div>
          <div style={{ opacity: iconOp }}>
            <FilmIcon size={130} />
          </div>
        </div>
        {/* accent line */}
        <div style={{ width: lineWidth, height: 3, background: `linear-gradient(90deg, ${accent}, ${mauve})`, margin: "0 auto", borderRadius: 2 }} />
        <div style={{ opacity: subtitleOp, transform: `translateY(${subtitleY}px)`, marginTop: 28 }}>
          <span style={{ fontSize: 38, color: sub, fontFamily: "system-ui, sans-serif" }}>
            Make videos with <span style={{ color: "#61dafb", fontWeight: 700 }}>React</span>
          </span>
        </div>
        <div style={{ opacity: tagOp, transform: `translateY(${tagY}px)`, marginTop: 16, display: "flex", gap: 12, justifyContent: "center" }}>
          {["Programmatic", "Deterministic", "Open Source"].map((t, i) => (
            <div key={i} style={{ background: surface, border: `1px solid ${sub}33`, borderRadius: 8, padding: "8px 20px", fontSize: 18, color: sub, fontFamily: "monospace" }}>
              {t}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── SCENE 2: How it works - Code to Video (90-180) ──
const CodeToVideoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const codeLines = [
    { text: "export const MyVideo = () => {", color: txt },
    { text: "  const frame = useCurrentFrame();", color: yellow },
    { text: "  const opacity = interpolate(", color: green },
    { text: "    frame, [0, 30], [0, 1]", color: green },
    { text: "  );", color: green },
    { text: "  return (", color: txt },
    { text: "    <h1 style={{ opacity }}>", color: accent },
    { text: '      Hello Remotion!', color: mauve },
    { text: "    </h1>", color: accent },
    { text: "  );", color: txt },
    { text: "};", color: txt },
  ];

  // Arrow animation
  const arrowOp = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const arrowX = interpolate(frame, [40, 55], [-20, 0], { extrapolateRight: "clamp" });

  // Result preview
  const previewOp = interpolate(frame, [50, 65], [0, 1], { extrapolateRight: "clamp" });
  const previewScale = spring({ frame: Math.max(0, frame - 50), fps, config: { damping: 14 } });
  const demoTextOp = interpolate(frame, [55, 80], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg, justifyContent: "center", alignItems: "center" }}>
      <Particles />
      <div style={{ opacity: titleOp, position: "absolute", top: 50, fontSize: 42, fontWeight: 700, color: txt, fontFamily: "system-ui, sans-serif", zIndex: 1 }}>
        <CodeBracket size={50} /> Write React, Get Video
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 60, zIndex: 1 }}>
        {/* Code editor mock */}
        <div style={{ background: crust, borderRadius: 16, border: `1px solid ${surface}`, width: 620, overflow: "hidden" }}>
          {/* Title bar */}
          <div style={{ display: "flex", gap: 8, padding: "14px 18px", background: "#181825", borderBottom: `1px solid ${surface}` }}>
            <div style={{ width: 12, height: 12, borderRadius: 6, background: red }} />
            <div style={{ width: 12, height: 12, borderRadius: 6, background: yellow }} />
            <div style={{ width: 12, height: 12, borderRadius: 6, background: green }} />
            <span style={{ marginLeft: 12, fontSize: 14, color: sub, fontFamily: "monospace" }}>MyVideo.tsx</span>
          </div>
          <div style={{ padding: "20px 24px", fontFamily: "monospace", fontSize: 18, lineHeight: 1.7 }}>
            {codeLines.map((line, i) => {
              const delay = i * 3;
              const op = interpolate(frame, [delay + 5, delay + 12], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
              return (
                <div key={i} style={{ opacity: op, color: line.color, whiteSpace: "pre" }}>
                  {line.text}
                </div>
              );
            })}
          </div>
        </div>

        {/* Arrow */}
        <div style={{ opacity: arrowOp, transform: `translateX(${arrowX}px)`, fontSize: 60, color: accent }}>
          {"\u2192"}
        </div>

        {/* Video preview */}
        <div style={{ opacity: previewOp, transform: `scale(${previewScale})` }}>
          <div style={{ background: crust, borderRadius: 16, border: `2px solid ${accent}`, width: 480, height: 300, display: "flex", justifyContent: "center", alignItems: "center", position: "relative", overflow: "hidden" }}>
            <div style={{ position: "absolute", top: 12, right: 16, fontSize: 13, color: sub, fontFamily: "monospace" }}>
              1920x1080 @ 30fps
            </div>
            <div style={{ fontSize: 56, fontWeight: 800, color: txt, opacity: demoTextOp, fontFamily: "system-ui, sans-serif" }}>
              Hello Remotion!
            </div>
            {/* Progress bar */}
            <div style={{ position: "absolute", bottom: 0, left: 0, height: 4, background: accent, width: interpolate(frame, [55, 85], [0, 480], { extrapolateRight: "clamp" }), borderRadius: 2 }} />
          </div>
          <div style={{ textAlign: "center", marginTop: 12, fontSize: 16, color: green, fontFamily: "monospace" }}>
            .mp4 output
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── SCENE 3: Core Concepts (180-270) ──
const ConceptsScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const cards = [
    {
      title: "Composition",
      color: accent,
      desc: "Define your video canvas",
      code: '<Composition fps={30} width={1920} height={1080} />',
    },
    {
      title: "Sequence",
      color: green,
      desc: "Order scenes on timeline",
      code: '<Sequence from={0} durationInFrames={90}>',
    },
    {
      title: "useCurrentFrame",
      color: yellow,
      desc: "Animate with frame numbers",
      code: "const frame = useCurrentFrame();",
    },
  ];

  return (
    <AbsoluteFill style={{ background: bg, justifyContent: "center", alignItems: "center" }}>
      <Particles />
      <div style={{ opacity: titleOp, position: "absolute", top: 55, fontSize: 42, fontWeight: 700, color: txt, fontFamily: "system-ui, sans-serif", zIndex: 1 }}>
        Core Concepts
      </div>

      <div style={{ display: "flex", gap: 40, zIndex: 1, marginTop: 40 }}>
        {cards.map((card, i) => {
          const delay = i * 10;
          const s = spring({ frame: Math.max(0, frame - delay - 5), fps, config: { damping: 12 } });
          const y = interpolate(frame, [delay + 5, delay + 20], [60, 0], { extrapolateRight: "clamp" });

          return (
            <div
              key={i}
              style={{
                transform: `scale(${s}) translateY(${y}px)`,
                background: crust,
                borderRadius: 20,
                border: `2px solid ${card.color}`,
                width: 420,
                padding: 0,
                overflow: "hidden",
              }}
            >
              {/* Top accent bar */}
              <div style={{ height: 5, background: card.color }} />
              <div style={{ padding: "32px 30px" }}>
                {/* Number badge */}
                <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 18 }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: card.color + "22", display: "flex", justifyContent: "center", alignItems: "center", fontSize: 20, fontWeight: 800, color: card.color, fontFamily: "monospace" }}>
                    {i + 1}
                  </div>
                  <div style={{ fontSize: 28, fontWeight: 700, color: card.color, fontFamily: "monospace" }}>
                    {card.title}
                  </div>
                </div>

                <div style={{ fontSize: 20, color: sub, marginBottom: 20 }}>
                  {card.desc}
                </div>

                {/* Code snippet */}
                <div style={{ background: bg, borderRadius: 10, padding: "14px 18px", border: `1px solid ${surface}` }}>
                  <code style={{ fontSize: 14, color: green, fontFamily: "monospace", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
                    {card.code}
                  </code>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// ── SCENE 4: Render Pipeline (270-360) ──
const PipelineScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  const steps = [
    { label: "React JSX", sub: "Components", color: accent, icon: "<>" },
    { label: "Bundler", sub: "Webpack", color: green, icon: "{}" },
    { label: "Renderer", sub: "Headless Chrome", color: yellow, icon: "[]" },
    { label: "MP4", sub: "H.264 Video", color: red, icon: ">" },
  ];

  return (
    <AbsoluteFill style={{ background: bg, justifyContent: "center", alignItems: "center" }}>
      <Particles />
      <div style={{ opacity: titleOp, position: "absolute", top: 55, fontSize: 42, fontWeight: 700, color: txt, fontFamily: "system-ui, sans-serif", zIndex: 1 }}>
        Render Pipeline
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 0, zIndex: 1, marginTop: 20 }}>
        {steps.map((step, i) => {
          const delay = i * 10;
          const s = spring({ frame: Math.max(0, frame - delay - 5), fps, config: { damping: 12 } });
          const arrowOp = interpolate(frame, [delay + 12, delay + 22], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

          // Glow pulse for active step
          const glowPhase = Math.max(0, frame - delay - 15);
          const glow = glowPhase > 0 && glowPhase < 30 ? Math.sin(glowPhase * 0.3) * 0.3 + 0.7 : 1;

          return (
            <React.Fragment key={i}>
              <div
                style={{
                  transform: `scale(${s})`,
                  background: crust,
                  border: `2px solid ${step.color}`,
                  borderRadius: 20,
                  width: 280,
                  padding: "36px 24px",
                  textAlign: "center",
                  boxShadow: `0 0 ${glow * 30}px ${step.color}44`,
                }}
              >
                <div style={{ fontSize: 36, marginBottom: 12, fontFamily: "monospace", color: step.color, fontWeight: 700 }}>
                  {step.icon}
                </div>
                <div style={{ fontSize: 28, fontWeight: 700, color: step.color, fontFamily: "monospace" }}>
                  {step.label}
                </div>
                <div style={{ fontSize: 18, color: sub, marginTop: 8 }}>
                  {step.sub}
                </div>
              </div>
              {i < steps.length - 1 && (
                <div style={{ opacity: arrowOp, fontSize: 44, color: sub, margin: "0 16px", fontFamily: "monospace" }}>
                  {"\u2192"}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* CLI command at bottom */}
      <div style={{
        position: "absolute",
        bottom: 80,
        opacity: interpolate(frame, [50, 65], [0, 1], { extrapolateRight: "clamp" }),
        transform: `translateY(${interpolate(frame, [50, 65], [20, 0], { extrapolateRight: "clamp" })}px)`,
        zIndex: 1,
      }}>
        <div style={{ background: crust, borderRadius: 12, padding: "16px 40px", border: `1px solid ${surface}`, fontFamily: "monospace", fontSize: 22 }}>
          <span style={{ color: green }}>$</span>{" "}
          <span style={{ color: txt }}>npx remotion render src/index.ts MyComp</span>{" "}
          <span style={{ color: sub }}>out.mp4</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── SCENE 5: Outro (360-450) ──
const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const scale = spring({ frame, fps, config: { damping: 10, mass: 0.7 } });
  const opacity = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp" });
  const atomRotate = frame * 2;

  const cmdOp = interpolate(frame, [30, 45], [0, 1], { extrapolateRight: "clamp" });
  const cmdY = interpolate(frame, [30, 45], [30, 0], { extrapolateRight: "clamp" });

  const badgeOp = interpolate(frame, [45, 60], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg, justifyContent: "center", alignItems: "center" }}>
      <Particles />
      <div style={{ transform: `scale(${scale})`, opacity, textAlign: "center", zIndex: 1 }}>
        <div style={{ transform: `rotate(${atomRotate}deg)`, marginBottom: 24 }}>
          <ReactAtom size={100} />
        </div>
        <div style={{ fontSize: 80, fontWeight: 900, color: txt, fontFamily: "system-ui, sans-serif", letterSpacing: -2 }}>
          Remot<span style={{ color: accent }}>ion</span>
        </div>
        <div style={{ fontSize: 30, color: sub, marginTop: 12, fontFamily: "system-ui, sans-serif" }}>
          Videos programaticos com React
        </div>

        {/* Get started command */}
        <div style={{ opacity: cmdOp, transform: `translateY(${cmdY}px)`, marginTop: 40 }}>
          <div style={{ background: crust, borderRadius: 14, padding: "18px 50px", border: `2px solid ${accent}`, display: "inline-block", fontFamily: "monospace", fontSize: 26 }}>
            <span style={{ color: green }}>$</span>{" "}
            <span style={{ color: txt }}>npx create-video@latest</span>
          </div>
        </div>

        {/* Tech badges */}
        <div style={{ opacity: badgeOp, marginTop: 28, display: "flex", gap: 14, justifyContent: "center" }}>
          {["React", "TypeScript", "Webpack", "FFmpeg", "Chromium"].map((t, i) => (
            <div key={i} style={{ background: surface, borderRadius: 8, padding: "6px 16px", fontSize: 16, color: sub, fontFamily: "monospace" }}>
              {t}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 24, fontSize: 18, color: sub + "88" }}>
          remotion.dev
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── Main Composition ──
export const ClaudeLauncherVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={90}>
        <TitleScene />
      </Sequence>
      <Sequence from={90} durationInFrames={90}>
        <CodeToVideoScene />
      </Sequence>
      <Sequence from={180} durationInFrames={90}>
        <ConceptsScene />
      </Sequence>
      <Sequence from={270} durationInFrames={90}>
        <PipelineScene />
      </Sequence>
      <Sequence from={360} durationInFrames={90}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};
