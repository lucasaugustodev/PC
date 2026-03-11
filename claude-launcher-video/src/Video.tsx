import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
} from "remotion";

const bg = "#1e1e2e";
const accent = "#89b4fa";
const green = "#a6e3a1";
const text = "#cdd6f4";
const subtext = "#a6adc8";
const surface = "#313244";
const crust = "#11111b";

const Intro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: bg,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          opacity,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 28,
            color: subtext,
            letterSpacing: 4,
            marginBottom: 20,
          }}
        >
          APRESENTANDO
        </div>
        <div
          style={{
            fontSize: 90,
            fontWeight: 800,
            color: text,
            fontFamily: "monospace",
          }}
        >
          Claude <span style={{ color: accent }}>Launcher</span> Web
        </div>
        <div style={{ fontSize: 32, color: subtext, marginTop: 24 }}>
          Gerencie sessoes Claude Code pelo navegador
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Architecture: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const boxes = [
    { label: "Browser", sub: "xterm.js + Preact", x: 160, color: accent },
    { label: "WebSocket", sub: "Tempo real", x: 560, color: "#f9e2af" },
    { label: "Express Server", sub: "Node.js :3001", x: 960, color: green },
    { label: "node-pty", sub: "Terminal PTY", x: 1360, color: "#f38ba8" },
  ];

  return (
    <AbsoluteFill
      style={{
        background: bg,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          fontSize: 48,
          fontWeight: 700,
          color: text,
          position: "absolute",
          top: 80,
        }}
      >
        Arquitetura
      </div>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          position: "relative",
          width: 1700,
          height: 300,
        }}
      >
        {boxes.map((box, i) => {
          const delay = i * 8;
          const s = spring({
            frame: Math.max(0, frame - delay),
            fps,
            config: { damping: 12 },
          });
          const arrowOp = interpolate(
            frame,
            [delay + 10, delay + 20],
            [0, 1],
            { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
          );
          return (
            <React.Fragment key={i}>
              <div
                style={{
                  position: "absolute",
                  left: box.x,
                  top: 80,
                  transform: `scale(${s})`,
                  background: surface,
                  border: `3px solid ${box.color}`,
                  borderRadius: 16,
                  padding: "30px 36px",
                  textAlign: "center",
                  width: 240,
                }}
              >
                <div
                  style={{ fontSize: 30, fontWeight: 700, color: box.color }}
                >
                  {box.label}
                </div>
                <div style={{ fontSize: 20, color: subtext, marginTop: 8 }}>
                  {box.sub}
                </div>
              </div>
              {i < boxes.length - 1 && (
                <div
                  style={{
                    position: "absolute",
                    left: box.x + 260,
                    top: 130,
                    opacity: arrowOp,
                    fontSize: 40,
                    color: subtext,
                  }}
                >
                  {"\u2192"}
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const Features: React.FC = () => {
  const frame = useCurrentFrame();

  const features = [
    {
      icon: "A",
      title: "Perfis de Projeto",
      desc: "Configure CWD, modo e prompt inicial",
    },
    {
      icon: "B",
      title: "Terminal ao Vivo",
      desc: "xterm.js com I/O bidirecional via WebSocket",
    },
    {
      icon: "C",
      title: "Historico de Sessoes",
      desc: "Filtre por status: completo, parado, crash",
    },
    {
      icon: "D",
      title: "Resume Sessoes",
      desc: "Retome sessoes com --continue",
    },
    {
      icon: "E",
      title: "GitHub Integrado",
      desc: "Clone, sync e crie repos direto da UI",
    },
    {
      icon: "F",
      title: "WhatsApp (Kapso)",
      desc: "Integracao com automacao WhatsApp",
    },
  ];

  return (
    <AbsoluteFill style={{ background: bg, padding: 80 }}>
      <div
        style={{ fontSize: 48, fontWeight: 700, color: text, marginBottom: 50 }}
      >
        Funcionalidades
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 30 }}>
        {features.map((f, i) => {
          const delay = i * 6;
          const y = interpolate(frame, [delay, delay + 15], [60, 0], {
            extrapolateRight: "clamp",
          });
          const op = interpolate(frame, [delay, delay + 15], [0, 1], {
            extrapolateRight: "clamp",
          });
          return (
            <div
              key={i}
              style={{
                background: surface,
                borderRadius: 16,
                padding: "28px 32px",
                width: 520,
                transform: `translateY(${y}px)`,
                opacity: op,
                borderLeft: `4px solid ${accent}`,
              }}
            >
              <div style={{ fontSize: 28, fontWeight: 700, color: text }}>
                [{f.icon}] {f.title}
              </div>
              <div style={{ fontSize: 22, color: subtext, marginTop: 8 }}>
                {f.desc}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

const MockUI: React.FC = () => {
  const frame = useCurrentFrame();

  const sidebarItems = [
    "Projetos",
    "Ativas",
    "Historico",
    "Agendamentos",
    "Arquivos",
    "Skills",
    "Marketplace",
    "Agentes",
  ];
  const termLines = [
    "$ claude --model opus --print 'Analise o codigo'",
    "",
    "+--------------------------------------+",
    "| Claude Code          session: abc123 |",
    "| Model: claude-opus-4-6               |",
    "| Mode: bypass                         |",
    "+--------------------------------------+",
    "",
    "> Analisando estrutura do projeto...",
    "> Encontrados 42 arquivos TypeScript",
    "> Gerando relatorio de analise...",
    "OK Analise completa em 3.2s",
  ];

  return (
    <AbsoluteFill style={{ background: crust }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          top: 0,
          bottom: 0,
          width: 260,
          background: "#181825",
          borderRight: `1px solid ${surface}`,
          padding: "30px 0",
        }}
      >
        <div
          style={{
            padding: "0 24px",
            marginBottom: 30,
            fontSize: 24,
            fontWeight: 700,
            color: accent,
          }}
        >
          Claude Launcher
        </div>
        {sidebarItems.map((item, i) => {
          const delay = i * 3;
          const op = interpolate(frame, [delay, delay + 10], [0, 1], {
            extrapolateRight: "clamp",
          });
          const active = i === 0;
          return (
            <div
              key={i}
              style={{
                padding: "12px 24px",
                fontSize: 20,
                color: active ? accent : subtext,
                background: active ? surface : "transparent",
                opacity: op,
                borderLeft: active
                  ? `3px solid ${accent}`
                  : "3px solid transparent",
              }}
            >
              {item}
            </div>
          );
        })}
      </div>

      <div
        style={{
          position: "absolute",
          left: 260,
          top: 0,
          right: 0,
          bottom: 0,
          padding: 40,
        }}
      >
        <div
          style={{
            fontSize: 32,
            fontWeight: 700,
            color: text,
            marginBottom: 20,
          }}
        >
          Sessao Ativa — <span style={{ color: green }}>*</span> projeto-demo
        </div>
        <div
          style={{
            background: "#0d0d0d",
            borderRadius: 12,
            padding: 30,
            fontFamily: "monospace",
            fontSize: 20,
            height: 700,
            border: `1px solid ${surface}`,
          }}
        >
          {termLines.map((line, i) => {
            const charDelay = i * 5;
            const op = interpolate(
              frame,
              [charDelay + 10, charDelay + 15],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }
            );
            const lineColor = line.startsWith("OK")
              ? green
              : line.startsWith(">")
                ? accent
                : text;
            return (
              <div
                key={i}
                style={{
                  opacity: op,
                  color: lineColor,
                  marginBottom: 4,
                  whiteSpace: "pre",
                }}
              >
                {line}
              </div>
            );
          })}
          <span
            style={{
              display: "inline-block",
              width: 12,
              height: 24,
              background: accent,
              opacity: Math.sin(frame * 0.3) > 0 ? 1 : 0,
              marginTop: 8,
            }}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const scale = spring({ frame, fps, config: { damping: 12 } });
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: bg,
        justifyContent: "center",
        alignItems: "center",
      }}
    >
      <div
        style={{
          transform: `scale(${scale})`,
          opacity,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 72,
            fontWeight: 800,
            color: text,
            fontFamily: "monospace",
          }}
        >
          Claude <span style={{ color: accent }}>Launcher</span> Web
        </div>
        <div style={{ fontSize: 36, color: green, marginTop: 30 }}>
          localhost:3001
        </div>
        <div style={{ fontSize: 28, color: subtext, marginTop: 20 }}>
          Node.js - Express - WebSocket - xterm.js - Docker
        </div>
        <div
          style={{
            marginTop: 50,
            background: accent,
            color: crust,
            padding: "16px 48px",
            borderRadius: 12,
            fontSize: 28,
            fontWeight: 700,
            display: "inline-block",
          }}
        >
          Open Source — Comece agora
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const ClaudeLauncherVideo: React.FC = () => {
  return (
    <AbsoluteFill>
      <Sequence from={0} durationInFrames={90}>
        <Intro />
      </Sequence>
      <Sequence from={90} durationInFrames={90}>
        <Architecture />
      </Sequence>
      <Sequence from={180} durationInFrames={90}>
        <Features />
      </Sequence>
      <Sequence from={270} durationInFrames={90}>
        <MockUI />
      </Sequence>
      <Sequence from={360} durationInFrames={90}>
        <Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
