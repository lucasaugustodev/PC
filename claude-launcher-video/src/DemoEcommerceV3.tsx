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
import { ZoomFade, SlideIn, StaggerText, AnimatedCounter } from "./Transitions";

const bg = "#0a0a0a";
const neon = "#00ff88";
const purple = "#a855f7";
const pink = "#ec4899";
const white = "#fafafa";
const gray = "#71717a";
const dark = "#18181b";

// ── Shared: Floating product photo ──
const FloatingPhoto: React.FC<{
  src: string;
  size: number;
  borderColor?: string;
}> = ({ src, size, borderColor = neon }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrance = spring({ frame, fps, config: { damping: 14 } });
  const floatY = Math.sin(frame * 0.06) * 10;
  const floatRotate = Math.sin(frame * 0.04) * 1.5;
  const shineX = interpolate(frame, [10, 50], [-150, 150], { extrapolateRight: "clamp" });

  return (
    <div style={{
      transform: `scale(${entrance}) translateY(${floatY}px) rotate(${floatRotate}deg)`,
      width: size, height: size,
      borderRadius: size * 0.06,
      overflow: "hidden",
      border: `2px solid ${borderColor}44`,
      boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 80px ${borderColor}12`,
      position: "relative",
    }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(${120 + frame * 0.5}deg, transparent 35%, rgba(255,255,255,0.1) 50%, transparent 65%)`,
      }} />
    </div>
  );
};

// ── Glow orbs background ──
const GlowBg: React.FC<{ color1?: string; color2?: string }> = ({ color1 = neon, color2 = purple }) => {
  const frame = useCurrentFrame();
  const x1 = 20 + Math.sin(frame * 0.02) * 10;
  const y1 = 25 + Math.cos(frame * 0.025) * 8;
  const x2 = 75 + Math.sin(frame * 0.018 + 2) * 10;
  const y2 = 70 + Math.cos(frame * 0.022 + 1) * 8;
  return (
    <>
      <div style={{ position: "absolute", left: `${x1}%`, top: `${y1}%`, width: 500, height: 500, borderRadius: "50%", background: `radial-gradient(circle, ${color1}14, transparent 70%)`, transform: "translate(-50%,-50%)" }} />
      <div style={{ position: "absolute", left: `${x2}%`, top: `${y2}%`, width: 400, height: 400, borderRadius: "50%", background: `radial-gradient(circle, ${color2}10, transparent 70%)`, transform: "translate(-50%,-50%)" }} />
    </>
  );
};

// ════════════════════════════════════════
// HORIZONTAL (1920x1080)
// ════════════════════════════════════════

const Scene1H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const badgePulse = Math.sin(frame * 0.2) * 0.05 + 1;
  const badgeOp = interpolate(frame, [3, 14], [0, 1], { extrapolateRight: "clamp" });
  const priceOp = interpolate(frame, [22, 36], [0, 1], { extrapolateRight: "clamp" });
  const priceY = spring({ frame: Math.max(0, frame - 22), fps, config: { damping: 12, stiffness: 100 } });
  const detailOp = interpolate(frame, [32, 44], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg />
      <div style={{ display: "flex", height: "100%", alignItems: "center", zIndex: 1, position: "relative" }}>
        <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
          <FloatingPhoto src="img/headphone1.jpg" size={520} />
        </div>
        <div style={{ flex: 1, paddingRight: 80 }}>
          <div style={{ opacity: badgeOp, transform: `scale(${badgePulse})`, display: "inline-block", background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "8px 22px", borderRadius: 20, fontSize: 16, fontWeight: 800, marginBottom: 28 }}>
            -40% OFF HOJE
          </div>
          <StaggerText text="Fone Bluetooth" fontSize={58} stagger={4} startFrame={6} />
          <StaggerText text="Pro Max X1" fontSize={58} color={neon} stagger={4} startFrame={14} />
          <div style={{ opacity: detailOp, fontSize: 20, color: gray, marginTop: 20, lineHeight: 1.7 }}>
            Cancelamento de ruido ativo | 48h bateria<br />Bluetooth 5.3 | IPX7 a prova d'agua
          </div>
          <div style={{ opacity: priceOp, marginTop: 28, transform: `translateY(${(1 - priceY) * 30}px)` }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <span style={{ fontSize: 60, fontWeight: 900, color: white }}>R$ </span>
              <AnimatedCounter to={199} startFrame={24} duration={20} fontSize={60} color={white} />
              <span style={{ fontSize: 32, color: neon, fontWeight: 700 }}>,90</span>
              <span style={{ fontSize: 24, color: gray, textDecoration: "line-through", marginLeft: 12 }}>R$ 329,90</span>
            </div>
            <div style={{ fontSize: 16, color: neon, marginTop: 6 }}>ou 12x de R$ 16,66 sem juros</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Scene2H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const photos = ["img/headphone1.jpg", "img/headphone2.jpg", "img/headphone3.jpg"];
  const stats = [
    { to: 4.8, label: "Avaliacao", sub: "12.847 reviews", decimals: 1 },
    { to: 50, label: "Mil vendidos", sub: "este mes", decimals: 0 },
  ];
  const features = [
    { t: "ANC Ativo", d: "98% cancelamento", c: neon },
    { t: "48h Bateria", d: "Carga rapida", c: purple },
    { t: "Bluetooth 5.3", d: "15m alcance", c: pink },
    { t: "IPX7", d: "A prova d'agua", c: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg color1={purple} color2={pink} />
      <div style={{ display: "flex", height: "100%", zIndex: 1, position: "relative" }}>
        <div style={{ flex: 0.9, padding: 40, display: "flex", gap: 14 }}>
          {photos.map((src, i) => {
            const delay = i * 6;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const zoom = interpolate(frame, [delay, delay + 80], [1.08, 1], { extrapolateRight: "clamp" });
            const isMain = i === 1;
            return (
              <div key={i} style={{ flex: isMain ? 2.2 : 1, borderRadius: 16, overflow: "hidden", transform: `scale(${s})`, border: isMain ? `2px solid ${neon}44` : "1px solid #333", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              </div>
            );
          })}
        </div>
        <div style={{ flex: 1.1, padding: "40px 50px 40px 20px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ display: "flex", gap: 16, marginBottom: 24 }}>
            {stats.map((s, i) => {
              const delay = i * 6 + 8;
              const sc = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
              return (
                <div key={i} style={{ transform: `scale(${sc})`, flex: 1, background: dark, borderRadius: 14, border: "1px solid #ffffff11", padding: "20px 16px", textAlign: "center" }}>
                  <AnimatedCounter to={s.to} startFrame={delay + 5} duration={20} fontSize={38} color={neon} decimals={s.decimals} suffix={i === 1 ? "K+" : ""} />
                  <div style={{ fontSize: 15, color: white, marginTop: 4 }}>{s.label}</div>
                  <div style={{ fontSize: 12, color: gray, marginTop: 2 }}>{s.sub}</div>
                </div>
              );
            })}
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
            {features.map((f, i) => {
              const delay = i * 3 + 22;
              const op = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateRight: "clamp" });
              const x = interpolate(frame, [delay, delay + 8], [20, 0], { extrapolateRight: "clamp" });
              return (
                <div key={i} style={{ opacity: op, transform: `translateX(${x}px)`, background: dark, borderRadius: 12, borderLeft: `3px solid ${f.c}`, padding: "14px 18px", width: 225 }}>
                  <div style={{ fontSize: 17, fontWeight: 700, color: white }}>{f.t}</div>
                  <div style={{ fontSize: 14, color: gray, marginTop: 3 }}>{f.d}</div>
                </div>
              );
            })}
          </div>
          <div style={{ opacity: interpolate(frame, [50, 62], [0, 1], { extrapolateRight: "clamp" }), background: dark, borderRadius: 12, padding: "14px 18px", marginTop: 14, border: "1px solid #ffffff08" }}>
            <span style={{ color: "#fbbf24", fontSize: 18 }}>* * * * *</span>
            <span style={{ fontSize: 14, color: gray, marginLeft: 10 }}>"Melhor custo-beneficio que ja vi" — Ana M.</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Scene3H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 80], [1.1, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const op = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: Math.max(0, frame - 18), fps, config: { damping: 8, stiffness: 100 } });
  const pulse = Math.sin(frame * 0.18) * 0.04 + 1;
  const urgOp = interpolate(frame, [30, 42], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(25px) brightness(0.25)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.55)" }} />
      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          <div style={{ fontSize: 22, color: neon, letterSpacing: 5, marginBottom: 10 }}>OFERTA RELAMPAGO</div>
          <StaggerText text="Fone Pro Max X1" fontSize={64} stagger={3} />
          <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 14, marginTop: 14 }}>
            <span style={{ fontSize: 26, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
            <span style={{ fontSize: 76, fontWeight: 900, color: neon }}>R$ </span>
            <AnimatedCounter to={199.9} startFrame={10} duration={18} fontSize={76} color={neon} decimals={0} />
          </div>
          <div style={{ transform: `scale(${btnScale * pulse})`, marginTop: 32 }}>
            <div style={{ background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "22px 80px", borderRadius: 16, fontSize: 30, fontWeight: 900, display: "inline-block", boxShadow: `0 0 50px ${neon}44` }}>
              COMPRAR AGORA
            </div>
          </div>
          <div style={{ opacity: urgOp, marginTop: 22, display: "flex", gap: 14, justifyContent: "center", alignItems: "center" }}>
            <div style={{ background: "#dc262622", border: "1px solid #dc262666", borderRadius: 10, padding: "7px 16px", display: "flex", alignItems: "center", gap: 7 }}>
              <div style={{ width: 7, height: 7, borderRadius: 4, background: "#dc2626", opacity: blink }} />
              <span style={{ color: "#fca5a5", fontSize: 14, fontFamily: "monospace" }}>23 unidades</span>
            </div>
            <span style={{ fontSize: 14, color: gray }}>Frete gratis | 12x sem juros</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Horizontal composition with transitions
export const EcommerceH: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={100}>
      <ZoomFade durationInFrames={100}><Scene1H /></ZoomFade>
    </Sequence>
    <Sequence from={95} durationInFrames={100}>
      <SlideIn durationInFrames={100} direction="right"><Scene2H /></SlideIn>
    </Sequence>
    <Sequence from={190} durationInFrames={100}>
      <ZoomFade durationInFrames={100}><Scene3H /></ZoomFade>
    </Sequence>
  </AbsoluteFill>
);

// ════════════════════════════════════════
// VERTICAL (1080x1920) — Reels/TikTok
// ════════════════════════════════════════

const Scene1V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const badgePulse = Math.sin(frame * 0.2) * 0.05 + 1;
  const badgeOp = interpolate(frame, [3, 14], [0, 1], { extrapolateRight: "clamp" });
  const priceOp = interpolate(frame, [28, 40], [0, 1], { extrapolateRight: "clamp" });
  const priceY = spring({ frame: Math.max(0, frame - 28), fps, config: { damping: 12 } });
  const detailOp = interpolate(frame, [36, 48], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg />
      <div style={{ display: "flex", flexDirection: "column", height: "100%", alignItems: "center", justifyContent: "center", padding: "60px 50px", zIndex: 1 }}>
        <div style={{ opacity: badgeOp, transform: `scale(${badgePulse})`, background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "8px 22px", borderRadius: 20, fontSize: 18, fontWeight: 800, marginBottom: 30 }}>
          -40% OFF HOJE
        </div>
        <FloatingPhoto src="img/headphone1.jpg" size={440} />
        <div style={{ marginTop: 36, textAlign: "center" }}>
          <StaggerText text="Fone Bluetooth" fontSize={48} stagger={4} startFrame={8} />
          <StaggerText text="Pro Max X1" fontSize={48} color={neon} stagger={4} startFrame={16} />
        </div>
        <div style={{ opacity: detailOp, fontSize: 18, color: gray, marginTop: 16, textAlign: "center", lineHeight: 1.6 }}>
          ANC Ativo | 48h Bateria | BT 5.3 | IPX7
        </div>
        <div style={{ opacity: priceOp, marginTop: 24, textAlign: "center", transform: `translateY(${(1 - priceY) * 25}px)` }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 10, justifyContent: "center" }}>
            <span style={{ fontSize: 22, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, justifyContent: "center", marginTop: 4 }}>
            <span style={{ fontSize: 56, fontWeight: 900, color: white }}>R$ </span>
            <AnimatedCounter to={199} startFrame={30} duration={18} fontSize={56} color={white} />
            <span style={{ fontSize: 30, color: neon, fontWeight: 700 }}>,90</span>
          </div>
          <div style={{ fontSize: 15, color: neon, marginTop: 6 }}>12x de R$ 16,66 sem juros</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Scene2V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const photos = ["img/headphone1.jpg", "img/headphone2.jpg", "img/headphone3.jpg"];
  const features = [
    { t: "ANC Ativo", d: "98% cancelamento", c: neon },
    { t: "48h Bateria", d: "Carga rapida 10min=3h", c: purple },
    { t: "Bluetooth 5.3", d: "Conexao estavel 15m", c: pink },
    { t: "IPX7", d: "Resiste chuva e suor", c: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg color1={purple} color2={pink} />
      <div style={{ padding: "50px 40px", display: "flex", flexDirection: "column", height: "100%", zIndex: 1, position: "relative" }}>
        {/* Photo strip horizontal */}
        <div style={{ display: "flex", gap: 12, height: 350 }}>
          {photos.map((src, i) => {
            const delay = i * 5;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const zoom = interpolate(frame, [delay, delay + 80], [1.08, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{ flex: i === 1 ? 1.8 : 1, borderRadius: 14, overflow: "hidden", transform: `scale(${s})`, border: i === 1 ? `2px solid ${neon}44` : "1px solid #333", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Stats */}
        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          {[
            { to: 4.8, l: "Avaliacao", d: 1, s: "" },
            { to: 50, l: "Mil vendidos", d: 0, s: "K+" },
            { to: 1, l: "Mais vendido", d: 0, s: "#" },
          ].map((st, i) => {
            const delay = i * 5 + 12;
            const sc = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            return (
              <div key={i} style={{ transform: `scale(${sc})`, flex: 1, background: dark, borderRadius: 12, padding: "16px 12px", textAlign: "center", border: "1px solid #ffffff0a" }}>
                <div style={{ fontSize: 30, fontWeight: 900, color: neon }}>{st.s === "#" ? "#" : ""}<AnimatedCounter to={st.to} startFrame={delay + 3} duration={16} fontSize={30} color={neon} decimals={st.d} />{st.s === "K+" ? "K+" : ""}</div>
                <div style={{ fontSize: 13, color: gray, marginTop: 2 }}>{st.l}</div>
              </div>
            );
          })}
        </div>

        {/* Features */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 20, flex: 1, justifyContent: "center" }}>
          {features.map((f, i) => {
            const delay = i * 3 + 24;
            const op = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateRight: "clamp" });
            const x = interpolate(frame, [delay, delay + 8], [30, 0], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{ opacity: op, transform: `translateX(${x}px)`, background: dark, borderRadius: 12, borderLeft: `3px solid ${f.c}`, padding: "14px 18px" }}>
                <div style={{ fontSize: 18, fontWeight: 700, color: white }}>{f.t}</div>
                <div style={{ fontSize: 14, color: gray, marginTop: 2 }}>{f.d}</div>
              </div>
            );
          })}
        </div>

        {/* Review */}
        <div style={{ opacity: interpolate(frame, [52, 64], [0, 1], { extrapolateRight: "clamp" }), background: dark, borderRadius: 12, padding: "14px 18px", border: "1px solid #ffffff08", marginTop: 10 }}>
          <span style={{ color: "#fbbf24", fontSize: 16 }}>* * * * *</span>
          <span style={{ fontSize: 14, color: gray, marginLeft: 8 }}>"Qualidade absurda pelo preco" — Pedro L.</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Scene3V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 80], [1.12, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const op = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: Math.max(0, frame - 16), fps, config: { damping: 8, stiffness: 100 } });
  const pulse = Math.sin(frame * 0.18) * 0.04 + 1;
  const urgOp = interpolate(frame, [28, 40], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(25px) brightness(0.22)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.5)" }} />
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "60px 40px", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          <div style={{ fontSize: 20, color: neon, letterSpacing: 5, marginBottom: 14 }}>OFERTA RELAMPAGO</div>
          <StaggerText text="Fone Pro" fontSize={54} stagger={3} />
          <StaggerText text="Max X1" fontSize={54} stagger={3} startFrame={6} />
          <div style={{ marginTop: 20 }}>
            <span style={{ fontSize: 22, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6, justifyContent: "center", marginTop: 8 }}>
            <span style={{ fontSize: 70, fontWeight: 900, color: neon }}>R$ </span>
            <AnimatedCounter to={199} startFrame={10} duration={16} fontSize={70} color={neon} />
            <span style={{ fontSize: 36, color: neon }}>,90</span>
          </div>
          <div style={{ transform: `scale(${btnScale * pulse})`, marginTop: 36 }}>
            <div style={{ background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "22px 60px", borderRadius: 16, fontSize: 28, fontWeight: 900, display: "inline-block", boxShadow: `0 0 50px ${neon}44` }}>
              COMPRAR AGORA
            </div>
          </div>
          <div style={{ opacity: urgOp, marginTop: 24, display: "flex", flexDirection: "column", gap: 10, alignItems: "center" }}>
            <div style={{ background: "#dc262622", border: "1px solid #dc262666", borderRadius: 10, padding: "8px 18px", display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 7, height: 7, borderRadius: 4, background: "#dc2626", opacity: blink }} />
              <span style={{ color: "#fca5a5", fontSize: 15, fontFamily: "monospace" }}>Restam 23 unidades</span>
            </div>
            <span style={{ fontSize: 14, color: gray }}>Frete gratis | 12x sem juros</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Vertical composition with transitions
export const EcommerceV: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={100}>
      <ZoomFade durationInFrames={100}><Scene1V /></ZoomFade>
    </Sequence>
    <Sequence from={95} durationInFrames={100}>
      <SlideIn durationInFrames={100} direction="up"><Scene2V /></SlideIn>
    </Sequence>
    <Sequence from={190} durationInFrames={100}>
      <ZoomFade durationInFrames={100}><Scene3V /></ZoomFade>
    </Sequence>
  </AbsoluteFill>
);
