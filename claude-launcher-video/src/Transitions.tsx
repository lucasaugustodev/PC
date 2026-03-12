import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from "remotion";

// ── Zoom fade transition (scene zooms in and fades out at end) ──
export const ZoomFade: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
  transitionFrames?: number;
}> = ({ children, durationInFrames, transitionFrames = 12 }) => {
  const frame = useCurrentFrame();

  // Fade in
  const fadeIn = interpolate(frame, [0, transitionFrames], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Zoom out at end
  const exitStart = durationInFrames - transitionFrames;
  const fadeOut = interpolate(frame, [exitStart, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const zoomOut = interpolate(frame, [exitStart, durationInFrames], [1, 1.15], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const opacity = Math.min(fadeIn, fadeOut);

  return (
    <AbsoluteFill
      style={{
        opacity,
        transform: frame > exitStart ? `scale(${zoomOut})` : undefined,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

// ── Slide transition (slides in from direction) ──
export const SlideIn: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
  direction?: "left" | "right" | "up" | "down";
  transitionFrames?: number;
}> = ({ children, durationInFrames, direction = "right", transitionFrames = 14 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.8, stiffness: 120 },
  });

  const exitStart = durationInFrames - transitionFrames;
  const exitProgress = interpolate(frame, [exitStart, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  let enterTransform = "";
  let exitTransform = "";
  const enterDist = (1 - progress) * 100;
  const exitDist = exitProgress * 100;

  switch (direction) {
    case "left":
      enterTransform = `translateX(${-enterDist}%)`;
      exitTransform = `translateX(${exitDist}%)`;
      break;
    case "right":
      enterTransform = `translateX(${enterDist}%)`;
      exitTransform = `translateX(${-exitDist}%)`;
      break;
    case "up":
      enterTransform = `translateY(${-enterDist}%)`;
      exitTransform = `translateY(${exitDist}%)`;
      break;
    case "down":
      enterTransform = `translateY(${enterDist}%)`;
      exitTransform = `translateY(${-exitDist}%)`;
      break;
  }

  const transform = frame > exitStart ? exitTransform : enterTransform;
  const opacity = frame > exitStart ? 1 - exitProgress : 1;

  return (
    <AbsoluteFill style={{ transform, opacity }}>
      {children}
    </AbsoluteFill>
  );
};

// ── Staggered text reveal (word by word) ──
export const StaggerText: React.FC<{
  text: string;
  startFrame?: number;
  stagger?: number;
  fontSize?: number;
  color?: string;
  fontWeight?: number;
  fontFamily?: string;
}> = ({
  text,
  startFrame = 0,
  stagger = 3,
  fontSize = 60,
  color = "#fafafa",
  fontWeight = 800,
  fontFamily = "system-ui, sans-serif",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0 16px" }}>
      {words.map((word, i) => {
        const delay = startFrame + i * stagger;
        const s = spring({
          frame: Math.max(0, frame - delay),
          fps,
          config: { damping: 12, mass: 0.6, stiffness: 150 },
        });
        const y = (1 - s) * 40;
        const opacity = interpolate(frame, [delay, delay + 4], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `translateY(${y}px)`,
              opacity,
              fontSize,
              fontWeight,
              color,
              fontFamily,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ── Counter animation ──
export const AnimatedCounter: React.FC<{
  from?: number;
  to: number;
  startFrame?: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  fontSize?: number;
  color?: string;
  decimals?: number;
}> = ({
  from = 0,
  to,
  startFrame = 0,
  duration = 25,
  prefix = "",
  suffix = "",
  fontSize = 60,
  color = "#fafafa",
  decimals = 0,
}) => {
  const frame = useCurrentFrame();
  const progress = interpolate(
    frame,
    [startFrame, startFrame + duration],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  // Ease out cubic
  const eased = 1 - Math.pow(1 - progress, 3);
  const value = from + (to - from) * eased;

  return (
    <span style={{ fontSize, fontWeight: 900, color, fontFamily: "system-ui" }}>
      {prefix}{value.toFixed(decimals)}{suffix}
    </span>
  );
};

// ── Text Slam (single word slams in with heavy overshoot) ──
export const TextSlam: React.FC<{
  text: string;
  startFrame?: number;
  fontSize?: number;
  color?: string;
  accentColor?: string;
}> = ({ text, startFrame = 0, fontSize = 100, color = "#fafafa", accentColor }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = text.split(" ");

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0 20px", justifyContent: "center" }}>
      {words.map((word, i) => {
        const delay = startFrame + i * 6;
        const s = spring({
          frame: Math.max(0, frame - delay),
          fps,
          config: { damping: 8, mass: 0.4, stiffness: 200 },
        });
        const scale = interpolate(s, [0, 1], [3, 1]);
        const opacity = interpolate(frame, [delay, delay + 3], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });

        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              transform: `scale(${scale})`,
              opacity,
              fontSize,
              fontWeight: 900,
              color: i === words.length - 1 && accentColor ? accentColor : color,
              fontFamily: "system-ui",
              textShadow: `0 4px 30px rgba(0,0,0,0.5)`,
            }}
          >
            {word}
          </span>
        );
      })}
    </div>
  );
};

// ── Circular Reveal transition ──
export const CircularReveal: React.FC<{
  children: React.ReactNode;
  durationInFrames: number;
  transitionFrames?: number;
  originX?: string;
  originY?: string;
}> = ({ children, durationInFrames, transitionFrames = 15, originX = "50%", originY = "50%" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const revealProgress = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.8, stiffness: 80 },
  });
  const maxRadius = 150; // percentage
  const radius = revealProgress * maxRadius;

  const exitStart = durationInFrames - transitionFrames;
  const exitProgress = interpolate(frame, [exitStart, durationInFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const clipRadius = frame > exitStart ? maxRadius * (1 - exitProgress) : radius;

  return (
    <AbsoluteFill
      style={{
        clipPath: `circle(${clipRadius}% at ${originX} ${originY})`,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

// ── Glassmorphism panel ──
export const GlassPanel: React.FC<{
  children: React.ReactNode;
  blur?: number;
  opacity?: number;
  borderRadius?: number;
  borderColor?: string;
  padding?: string;
  style?: React.CSSProperties;
}> = ({ children, blur = 16, opacity = 0.15, borderRadius = 20, borderColor = "rgba(255,255,255,0.12)", padding = "32px", style }) => (
  <div style={{
    background: `rgba(255,255,255,${opacity})`,
    backdropFilter: `blur(${blur}px)`,
    WebkitBackdropFilter: `blur(${blur}px)`,
    borderRadius,
    border: `1px solid ${borderColor}`,
    padding,
    ...style,
  }}>
    {children}
  </div>
);

// ── Film grain overlay ──
export const FilmGrain: React.FC<{ opacity?: number }> = ({ opacity = 0.04 }) => {
  const frame = useCurrentFrame();
  // Shift noise pattern each frame using background-position
  const x = (frame * 97) % 300;
  const y = (frame * 131) % 300;
  return (
    <div style={{
      position: "absolute", inset: 0, zIndex: 999, pointerEvents: "none",
      opacity,
      backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`,
      backgroundPosition: `${x}px ${y}px`,
    }} />
  );
};
