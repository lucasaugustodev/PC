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
