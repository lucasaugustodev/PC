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

const bg = "#0a0a0a";
const neon = "#00ff88";
const purple = "#a855f7";
const pink = "#ec4899";
const white = "#fafafa";
const gray = "#71717a";
const dark = "#18181b";

// ── CENA 1: Product Hero with real photo ──
const ProductHero: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const photoScale = spring({ frame, fps, config: { damping: 14 } });
  const photoFloat = Math.sin(frame * 0.08) * 8;
  const glowSize = interpolate(frame, [0, 30], [0, 600], { extrapolateRight: "clamp" });
  const titleOp = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp" });
  const titleX = interpolate(frame, [10, 25], [-40, 0], { extrapolateRight: "clamp" });
  const priceOp = interpolate(frame, [25, 40], [0, 1], { extrapolateRight: "clamp" });
  const priceY = interpolate(frame, [25, 40], [30, 0], { extrapolateRight: "clamp" });
  const badgePulse = Math.sin(frame * 0.2) * 0.05 + 1;
  const badgeOp = interpolate(frame, [5, 18], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg }}>
      {/* Ambient glow */}
      <div style={{ position: "absolute", top: "20%", left: "15%", width: glowSize, height: glowSize, borderRadius: "50%", background: `radial-gradient(circle, ${neon}12, transparent 70%)` }} />
      <div style={{ position: "absolute", bottom: "10%", right: "10%", width: glowSize * 0.6, height: glowSize * 0.6, borderRadius: "50%", background: `radial-gradient(circle, ${purple}10, transparent 70%)` }} />

      <div style={{ display: "flex", height: "100%", alignItems: "center", zIndex: 1, position: "relative" }}>
        {/* Left - Product Photo */}
        <div style={{ flex: 1, display: "flex", justifyContent: "center", alignItems: "center" }}>
          <div style={{
            transform: `scale(${photoScale}) translateY(${photoFloat}px)`,
            width: 520, height: 520,
            borderRadius: 30,
            overflow: "hidden",
            border: `2px solid ${neon}33`,
            boxShadow: `0 20px 80px rgba(0,0,0,0.5), 0 0 60px ${neon}15`,
            position: "relative",
          }}>
            <Img src={staticFile("img/headphone1.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            {/* Shine effect */}
            <div style={{
              position: "absolute", inset: 0,
              background: `linear-gradient(135deg, transparent 30%, rgba(255,255,255,0.08) 50%, transparent 70%)`,
              transform: `translateX(${interpolate(frame, [0, 60], [-200, 200], { extrapolateRight: "clamp" })}%)`,
            }} />
          </div>
        </div>

        {/* Right - Info */}
        <div style={{ flex: 1, padding: "0 80px 0 0" }}>
          <div style={{ opacity: badgeOp, transform: `scale(${badgePulse})`, display: "inline-block", background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "8px 20px", borderRadius: 20, fontSize: 16, fontWeight: 800, marginBottom: 24 }}>
            -40% OFF HOJE
          </div>

          <div style={{ opacity: titleOp, transform: `translateX(${titleX}px)` }}>
            <div style={{ fontSize: 62, fontWeight: 800, color: white, fontFamily: "system-ui", lineHeight: 1.1 }}>
              Fone Bluetooth<br />
              <span style={{ color: neon }}>Pro Max X1</span>
            </div>

            <div style={{ fontSize: 20, color: gray, marginTop: 20, lineHeight: 1.7 }}>
              Cancelamento de ruído ativo | 48h bateria<br />
              Bluetooth 5.3 | IPX7 a prova d'água
            </div>
          </div>

          <div style={{ opacity: priceOp, transform: `translateY(${priceY}px)`, marginTop: 30 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 16 }}>
              <span style={{ fontSize: 64, fontWeight: 900, color: white, fontFamily: "system-ui" }}>
                R$ 199<span style={{ fontSize: 32, color: neon }}>,90</span>
              </span>
              <span style={{ fontSize: 26, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
            </div>
            <div style={{ fontSize: 17, color: neon, marginTop: 6 }}>ou 12x de R$ 16,66 sem juros</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── CENA 2: Multiple angles + Social Proof ──
const SocialScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const photos = ["img/headphone1.jpg", "img/headphone2.jpg", "img/headphone3.jpg"];

  const stats = [
    { num: "4.8", label: "Avaliação", sub: "12.847 reviews" },
    { num: "50K+", label: "Vendidos", sub: "este mes" },
    { num: "#1", label: "Mais Vendido", sub: "audio" },
  ];

  const features = [
    { title: "ANC Ativo", desc: "98% cancelamento", color: neon },
    { title: "48h Bateria", desc: "Carga rápida 10min=3h", color: purple },
    { title: "Bluetooth 5.3", desc: "Conexão 15m", color: pink },
    { title: "IPX7", desc: "Resiste chuva e suor", color: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <div style={{ display: "flex", height: "100%" }}>
        {/* Left - Photo carousel */}
        <div style={{ flex: 0.9, padding: 40, display: "flex", gap: 16 }}>
          {photos.map((src, i) => {
            const delay = i * 8;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const isMain = i === 1;
            return (
              <div key={i} style={{
                flex: isMain ? 2 : 1,
                borderRadius: 16,
                overflow: "hidden",
                transform: `scale(${s})`,
                border: isMain ? `2px solid ${neon}44` : `1px solid #333`,
              }}>
                <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
            );
          })}
        </div>

        {/* Right - Stats + Features */}
        <div style={{ flex: 1.1, padding: "40px 50px 40px 20px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {/* Stats */}
          <div style={{ display: "flex", gap: 16, marginBottom: 30 }}>
            {stats.map((s, i) => {
              const delay = i * 5 + 10;
              const sc = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
              return (
                <div key={i} style={{ transform: `scale(${sc})`, flex: 1, background: dark, borderRadius: 14, border: "1px solid #ffffff11", padding: "20px 16px", textAlign: "center" }}>
                  <div style={{ fontSize: 36, fontWeight: 900, color: neon, fontFamily: "system-ui" }}>{s.num}</div>
                  <div style={{ fontSize: 15, color: white, marginTop: 2 }}>{s.label}</div>
                  <div style={{ fontSize: 12, color: gray, marginTop: 2 }}>{s.sub}</div>
                </div>
              );
            })}
          </div>

          {/* Features */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {features.map((f, i) => {
              const delay = i * 4 + 25;
              const op = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
              return (
                <div key={i} style={{ opacity: op, background: dark, borderRadius: 12, borderLeft: `3px solid ${f.color}`, padding: "16px 20px", width: 230 }}>
                  <div style={{ fontSize: 18, fontWeight: 700, color: white }}>{f.title}</div>
                  <div style={{ fontSize: 14, color: gray, marginTop: 4 }}>{f.desc}</div>
                </div>
              );
            })}
          </div>

          {/* Review */}
          <div style={{
            opacity: interpolate(frame, [55, 70], [0, 1], { extrapolateRight: "clamp" }),
            background: dark, borderRadius: 12, padding: "16px 20px", marginTop: 16, border: "1px solid #ffffff08",
          }}>
            <div style={{ color: "#fbbf24", fontSize: 20, marginBottom: 6 }}>* * * * *</div>
            <div style={{ fontSize: 15, color: gray, fontStyle: "italic" }}>"Melhor fone que ja tive. Cancelamento de ruido perfeito." — Ana M.</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── CENA 3: CTA with photo background ──
const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const zoom = interpolate(frame, [0, 90], [1.1, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const op = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: Math.max(0, frame - 20), fps, config: { damping: 8 } });
  const pulse = Math.sin(frame * 0.18) * 0.04 + 1;
  const urgOp = interpolate(frame, [35, 50], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      {/* Blurred photo background */}
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(20px) brightness(0.3)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.6)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          <div style={{ fontSize: 24, color: neon, letterSpacing: 4, marginBottom: 12 }}>OFERTA RELAMPAGO</div>
          <div style={{ fontSize: 68, fontWeight: 900, color: white, fontFamily: "system-ui" }}>
            Fone Pro Max X1
          </div>
          <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, marginTop: 12 }}>
            <span style={{ fontSize: 28, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
            <span style={{ fontSize: 80, fontWeight: 900, color: neon, fontFamily: "system-ui" }}>R$ 199,90</span>
          </div>

          <div style={{ transform: `scale(${btnScale * pulse})`, marginTop: 36 }}>
            <div style={{
              background: `linear-gradient(135deg, ${neon}, #00cc6a)`,
              color: bg, padding: "22px 80px", borderRadius: 16,
              fontSize: 30, fontWeight: 900, display: "inline-block",
              fontFamily: "system-ui",
              boxShadow: `0 0 50px ${neon}44`,
            }}>
              COMPRAR AGORA
            </div>
          </div>

          <div style={{ opacity: urgOp, marginTop: 24, display: "flex", gap: 16, justifyContent: "center", alignItems: "center" }}>
            <div style={{ background: "#dc262622", border: "1px solid #dc262666", borderRadius: 10, padding: "8px 18px", display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: 4, background: "#dc2626", opacity: blink }} />
              <span style={{ color: "#fca5a5", fontSize: 15, fontFamily: "monospace" }}>23 unidades</span>
            </div>
            <span style={{ fontSize: 15, color: gray }}>Frete gratis | 12x sem juros</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const DemoEcommerce: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={90}><ProductHero /></Sequence>
    <Sequence from={90} durationInFrames={90}><SocialScene /></Sequence>
    <Sequence from={180} durationInFrames={90}><CTAScene /></Sequence>
  </AbsoluteFill>
);
