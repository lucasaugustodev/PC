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
import {
  TextSlam,
  CircularReveal,
  GlassPanel,
  FilmGrain,
  StaggerText,
  AnimatedCounter,
} from "./Transitions";

// ── Design tokens (corrected typography) ──
const bg = "#0a0a0a";
const neon = "#00ff88";
const purple = "#a855f7";
const pink = "#ec4899";
const white = "#fafafa";
const gray = "#a1a1aa";
const dark = "#18181b";

// Min font sizes: headline 80-120px, subhead 48-60px, body 40px+, label 36px+

// ── Shared: Floating product with parallax layers ──
const FloatingPhoto: React.FC<{
  src: string;
  size: number;
  borderColor?: string;
}> = ({ src, size, borderColor = neon }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const entrance = spring({ frame, fps, config: { damping: 14 } });
  const floatY = Math.sin(frame * 0.06) * 12;
  const floatRotate = Math.sin(frame * 0.04) * 2;
  const shineAngle = 120 + frame * 0.5;

  return (
    <div style={{
      transform: `scale(${entrance}) translateY(${floatY}px) rotate(${floatRotate}deg)`,
      width: size, height: size,
      borderRadius: size * 0.06,
      overflow: "hidden",
      border: `2px solid ${borderColor}44`,
      boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 100px ${borderColor}18`,
      position: "relative",
    }}>
      <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(${shineAngle}deg, transparent 30%, rgba(255,255,255,0.12) 50%, transparent 70%)`,
      }} />
    </div>
  );
};

// ── Animated glow orbs ──
const GlowBg: React.FC<{ color1?: string; color2?: string }> = ({ color1 = neon, color2 = purple }) => {
  const frame = useCurrentFrame();
  const x1 = 20 + Math.sin(frame * 0.02) * 12;
  const y1 = 25 + Math.cos(frame * 0.025) * 10;
  const x2 = 78 + Math.sin(frame * 0.018 + 2) * 12;
  const y2 = 72 + Math.cos(frame * 0.022 + 1) * 10;
  return (
    <>
      <div style={{ position: "absolute", left: `${x1}%`, top: `${y1}%`, width: 600, height: 600, borderRadius: "50%", background: `radial-gradient(circle, ${color1}18, transparent 70%)`, transform: "translate(-50%,-50%)" }} />
      <div style={{ position: "absolute", left: `${x2}%`, top: `${y2}%`, width: 500, height: 500, borderRadius: "50%", background: `radial-gradient(circle, ${color2}14, transparent 70%)`, transform: "translate(-50%,-50%)" }} />
    </>
  );
};

// ════════════════════════════════════════
// HORIZONTAL (1920x1080) — Safe zone: 80px margins
// ════════════════════════════════════════

const Scene1H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const badgePulse = Math.sin(frame * 0.2) * 0.05 + 1;
  const badgeOp = interpolate(frame, [3, 14], [0, 1], { extrapolateRight: "clamp" });
  const priceOp = interpolate(frame, [30, 44], [0, 1], { extrapolateRight: "clamp" });
  const priceY = spring({ frame: Math.max(0, frame - 30), fps, config: { damping: 12, stiffness: 100 } });
  const detailOp = interpolate(frame, [40, 52], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg />
      <div style={{ display: "flex", height: "100%", alignItems: "center", zIndex: 1, position: "relative", padding: "0 80px" }}>
        {/* Left - Product */}
        <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
          <FloatingPhoto src="img/headphone1.jpg" size={500} />
        </div>

        {/* Right - Info with glassmorphism */}
        <div style={{ flex: 1 }}>
          <div style={{ opacity: badgeOp, transform: `scale(${badgePulse})`, display: "inline-block", background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "10px 28px", borderRadius: 24, fontSize: 36, fontWeight: 800, marginBottom: 32 }}>
            -40% OFF
          </div>

          <TextSlam text="Fone Bluetooth" fontSize={84} startFrame={5} accentColor={neon} />
          <div style={{ marginTop: 8 }}>
            <TextSlam text="Pro Max X1" fontSize={84} startFrame={12} color={neon} />
          </div>

          <GlassPanel blur={20} opacity={0.08} borderRadius={16} padding="24px 32px" style={{ marginTop: 28, opacity: detailOp }}>
            <div style={{ fontSize: 40, color: gray, lineHeight: 1.6 }}>
              Cancelamento de ruido ativo<br />48h bateria | Bluetooth 5.3
            </div>
          </GlassPanel>

          <div style={{ opacity: priceOp, marginTop: 28, transform: `translateY(${(1 - priceY) * 30}px)` }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <span style={{ fontSize: 48, color: gray, textDecoration: "line-through" }}>R$ 329</span>
              <span style={{ fontSize: 96, fontWeight: 900, color: white, fontFamily: "system-ui" }}>R$</span>
              <AnimatedCounter to={199} startFrame={32} duration={18} fontSize={96} color={white} />
              <span style={{ fontSize: 48, color: neon, fontWeight: 700 }}>,90</span>
            </div>
          </div>
        </div>
      </div>
      <FilmGrain />
    </AbsoluteFill>
  );
};

const Scene2H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const photos = ["img/headphone1.jpg", "img/headphone2.jpg", "img/headphone3.jpg"];
  const features = [
    { t: "ANC Ativo", d: "98% cancelamento", c: neon },
    { t: "48h Bateria", d: "Carga rapida", c: purple },
    { t: "BT 5.3", d: "15m alcance", c: pink },
    { t: "IPX7", d: "A prova d'agua", c: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg color1={purple} color2={pink} />
      <div style={{ display: "flex", height: "100%", zIndex: 1, position: "relative", padding: "40px 80px" }}>
        {/* Left - Photo grid */}
        <div style={{ flex: 0.9, display: "flex", gap: 16 }}>
          {photos.map((src, i) => {
            const delay = i * 6;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const zoom = interpolate(frame, [delay, delay + 80], [1.1, 1], { extrapolateRight: "clamp" });
            const isMain = i === 1;
            return (
              <div key={i} style={{ flex: isMain ? 2.2 : 1, borderRadius: 20, overflow: "hidden", transform: `scale(${s})`, border: isMain ? `2px solid ${neon}44` : "1px solid #333", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Right - Stats + Features */}
        <div style={{ flex: 1.1, paddingLeft: 40, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {/* Stats in glass panels */}
          <div style={{ display: "flex", gap: 16, marginBottom: 28 }}>
            {[
              { to: 4.8, label: "Avaliacao", decimals: 1, suffix: "" },
              { to: 50, label: "Mil vendidos", decimals: 0, suffix: "K+" },
            ].map((s, i) => {
              const delay = i * 6 + 8;
              const sc = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
              return (
                <GlassPanel key={i} blur={20} opacity={0.1} borderRadius={16} padding="24px 20px" style={{ transform: `scale(${sc})`, flex: 1, textAlign: "center" }}>
                  <AnimatedCounter to={s.to} startFrame={delay + 5} duration={18} fontSize={56} color={neon} decimals={s.decimals} suffix={s.suffix} />
                  <div style={{ fontSize: 36, color: white, marginTop: 6 }}>{s.label}</div>
                </GlassPanel>
              );
            })}
          </div>

          {/* Features */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
            {features.map((f, i) => {
              const delay = i * 3 + 22;
              const op = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateRight: "clamp" });
              const x = interpolate(frame, [delay, delay + 8], [30, 0], { extrapolateRight: "clamp" });
              return (
                <GlassPanel key={i} blur={16} opacity={0.08} borderRadius={14} padding="18px 22px" style={{ opacity: op, transform: `translateX(${x}px)`, width: 240, borderLeft: `4px solid ${f.c}` }}>
                  <div style={{ fontSize: 40, fontWeight: 700, color: white }}>{f.t}</div>
                  <div style={{ fontSize: 36, color: gray, marginTop: 4 }}>{f.d}</div>
                </GlassPanel>
              );
            })}
          </div>

          {/* Review */}
          <GlassPanel blur={16} opacity={0.06} borderRadius={14} padding="18px 22px" style={{ opacity: interpolate(frame, [50, 62], [0, 1], { extrapolateRight: "clamp" }), marginTop: 16 }}>
            <span style={{ color: "#fbbf24", fontSize: 40 }}>*****</span>
            <span style={{ fontSize: 36, color: gray, marginLeft: 14 }}>"Melhor custo-beneficio" — Ana M.</span>
          </GlassPanel>
        </div>
      </div>
      <FilmGrain />
    </AbsoluteFill>
  );
};

const Scene3H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 80], [1.1, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const op = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: Math.max(0, frame - 20), fps, config: { damping: 8, stiffness: 100 } });
  const pulse = Math.sin(frame * 0.18) * 0.04 + 1;
  const urgOp = interpolate(frame, [32, 44], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      {/* Blurred photo bg */}
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(30px) brightness(0.22)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.5)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          <div style={{ fontSize: 44, color: neon, letterSpacing: 6, marginBottom: 16 }}>OFERTA RELAMPAGO</div>

          <TextSlam text="Pro Max X1" fontSize={100} startFrame={4} accentColor={neon} />

          <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, marginTop: 20 }}>
            <span style={{ fontSize: 44, color: gray, textDecoration: "line-through" }}>R$ 329</span>
            <span style={{ fontSize: 110, fontWeight: 900, color: neon, fontFamily: "system-ui" }}>R$</span>
            <AnimatedCounter to={199} startFrame={12} duration={16} fontSize={110} color={neon} />
            <span style={{ fontSize: 52, color: neon }}>,90</span>
          </div>

          <div style={{ transform: `scale(${btnScale * pulse})`, marginTop: 40 }}>
            <div style={{
              background: `linear-gradient(135deg, ${neon}, #00cc6a)`,
              color: bg, padding: "24px 90px", borderRadius: 18,
              fontSize: 44, fontWeight: 900, display: "inline-block",
              boxShadow: `0 0 60px ${neon}44, 0 0 120px ${neon}18`,
            }}>
              COMPRAR AGORA
            </div>
          </div>

          <div style={{ opacity: urgOp, marginTop: 28, display: "flex", gap: 16, justifyContent: "center", alignItems: "center" }}>
            <GlassPanel blur={12} opacity={0.12} borderRadius={12} padding="10px 24px" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: 5, background: "#dc2626", opacity: blink }} />
              <span style={{ color: "#fca5a5", fontSize: 36, fontFamily: "monospace" }}>23 unidades</span>
            </GlassPanel>
            <span style={{ fontSize: 36, color: gray }}>Frete gratis</span>
          </div>
        </div>
      </div>
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};

// Horizontal composition: ZoomFade → CircularReveal → ZoomFade
export const EcommerceV4H: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={100}>
      <CircularReveal durationInFrames={100} transitionFrames={12}><Scene1H /></CircularReveal>
    </Sequence>
    <Sequence from={95} durationInFrames={100}>
      <CircularReveal durationInFrames={100} originX="30%" originY="40%"><Scene2H /></CircularReveal>
    </Sequence>
    <Sequence from={190} durationInFrames={105}>
      <CircularReveal durationInFrames={105} originX="50%" originY="60%"><Scene3H /></CircularReveal>
    </Sequence>
  </AbsoluteFill>
);

// ════════════════════════════════════════
// VERTICAL (1080x1920) — Safe zone: center 900x1492
// ════════════════════════════════════════

const Scene1V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const badgePulse = Math.sin(frame * 0.2) * 0.05 + 1;
  const badgeOp = interpolate(frame, [3, 14], [0, 1], { extrapolateRight: "clamp" });
  const priceOp = interpolate(frame, [34, 46], [0, 1], { extrapolateRight: "clamp" });
  const priceY = spring({ frame: Math.max(0, frame - 34), fps, config: { damping: 12 } });
  const detailOp = interpolate(frame, [42, 54], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg />
      {/* Safe zone container: 90px horizontal, 214px vertical padding */}
      <div style={{ display: "flex", flexDirection: "column", height: "100%", alignItems: "center", justifyContent: "center", padding: "214px 90px", zIndex: 1 }}>
        <div style={{ opacity: badgeOp, transform: `scale(${badgePulse})`, background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "10px 28px", borderRadius: 24, fontSize: 36, fontWeight: 800, marginBottom: 32 }}>
          -40% OFF
        </div>

        <FloatingPhoto src="img/headphone1.jpg" size={420} />

        <div style={{ marginTop: 36, textAlign: "center" }}>
          <TextSlam text="Fone Pro" fontSize={72} startFrame={8} />
          <TextSlam text="Max X1" fontSize={72} startFrame={14} color={neon} />
        </div>

        <GlassPanel blur={20} opacity={0.08} borderRadius={16} padding="20px 28px" style={{ marginTop: 24, opacity: detailOp, textAlign: "center" }}>
          <div style={{ fontSize: 40, color: gray, lineHeight: 1.5 }}>
            ANC | 48h | BT 5.3 | IPX7
          </div>
        </GlassPanel>

        <div style={{ opacity: priceOp, marginTop: 28, textAlign: "center", transform: `translateY(${(1 - priceY) * 25}px)` }}>
          <span style={{ fontSize: 40, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, justifyContent: "center", marginTop: 8 }}>
            <span style={{ fontSize: 80, fontWeight: 900, color: white, fontFamily: "system-ui" }}>R$</span>
            <AnimatedCounter to={199} startFrame={36} duration={16} fontSize={80} color={white} />
            <span style={{ fontSize: 44, color: neon, fontWeight: 700 }}>,90</span>
          </div>
        </div>
      </div>
      <FilmGrain />
    </AbsoluteFill>
  );
};

const Scene2V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const photos = ["img/headphone1.jpg", "img/headphone2.jpg", "img/headphone3.jpg"];
  const features = [
    { t: "ANC Ativo", d: "98%", c: neon },
    { t: "48h Bateria", d: "Rapida", c: purple },
    { t: "BT 5.3", d: "15m", c: pink },
    { t: "IPX7", d: "Agua", c: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg color1={purple} color2={pink} />
      <div style={{ padding: "214px 90px", display: "flex", flexDirection: "column", height: "100%", zIndex: 1, position: "relative" }}>
        {/* Photo strip */}
        <div style={{ display: "flex", gap: 12, height: 320 }}>
          {photos.map((src, i) => {
            const delay = i * 5;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const zoom = interpolate(frame, [delay, delay + 80], [1.1, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{ flex: i === 1 ? 1.8 : 1, borderRadius: 16, overflow: "hidden", transform: `scale(${s})`, border: i === 1 ? `2px solid ${neon}44` : "1px solid #333", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              </div>
            );
          })}
        </div>

        {/* Stats */}
        <div style={{ display: "flex", gap: 14, marginTop: 24 }}>
          {[
            { to: 4.8, l: "Nota", d: 1, s: "" },
            { to: 50, l: "Mil vendas", d: 0, s: "K+" },
          ].map((st, i) => {
            const delay = i * 5 + 12;
            const sc = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            return (
              <GlassPanel key={i} blur={16} opacity={0.1} borderRadius={14} padding="20px 16px" style={{ transform: `scale(${sc})`, flex: 1, textAlign: "center" }}>
                <AnimatedCounter to={st.to} startFrame={delay + 3} duration={16} fontSize={48} color={neon} decimals={st.d} suffix={st.s} />
                <div style={{ fontSize: 36, color: gray, marginTop: 4 }}>{st.l}</div>
              </GlassPanel>
            );
          })}
        </div>

        {/* Features grid */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 20, flex: 1, alignContent: "center" }}>
          {features.map((f, i) => {
            const delay = i * 3 + 24;
            const op = interpolate(frame, [delay, delay + 8], [0, 1], { extrapolateRight: "clamp" });
            return (
              <GlassPanel key={i} blur={14} opacity={0.08} borderRadius={12} padding="16px 20px" style={{ opacity: op, flex: "1 1 40%", borderLeft: `4px solid ${f.c}` }}>
                <div style={{ fontSize: 40, fontWeight: 700, color: white }}>{f.t}</div>
                <div style={{ fontSize: 36, color: gray, marginTop: 2 }}>{f.d}</div>
              </GlassPanel>
            );
          })}
        </div>

        {/* Review */}
        <GlassPanel blur={14} opacity={0.06} borderRadius={12} padding="16px 20px" style={{ opacity: interpolate(frame, [52, 64], [0, 1], { extrapolateRight: "clamp" }), marginTop: 12 }}>
          <span style={{ color: "#fbbf24", fontSize: 36 }}>*****</span>
          <span style={{ fontSize: 36, color: gray, marginLeft: 10 }}>"Qualidade absurda" — Pedro</span>
        </GlassPanel>
      </div>
      <FilmGrain />
    </AbsoluteFill>
  );
};

const Scene3V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 80], [1.12, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const op = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: Math.max(0, frame - 18), fps, config: { damping: 8, stiffness: 100 } });
  const pulse = Math.sin(frame * 0.18) * 0.04 + 1;
  const urgOp = interpolate(frame, [30, 42], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(30px) brightness(0.2)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.45)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "214px 90px", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          <div style={{ fontSize: 40, color: neon, letterSpacing: 6, marginBottom: 20 }}>OFERTA RELAMPAGO</div>

          <TextSlam text="Pro Max" fontSize={80} startFrame={4} />
          <TextSlam text="X1" fontSize={80} startFrame={10} color={neon} />

          <div style={{ marginTop: 24 }}>
            <span style={{ fontSize: 40, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, justifyContent: "center", marginTop: 12 }}>
            <span style={{ fontSize: 96, fontWeight: 900, color: neon, fontFamily: "system-ui" }}>R$</span>
            <AnimatedCounter to={199} startFrame={12} duration={14} fontSize={96} color={neon} />
            <span style={{ fontSize: 48, color: neon }}>,90</span>
          </div>

          <div style={{ transform: `scale(${btnScale * pulse})`, marginTop: 40 }}>
            <div style={{
              background: `linear-gradient(135deg, ${neon}, #00cc6a)`,
              color: bg, padding: "24px 70px", borderRadius: 18,
              fontSize: 44, fontWeight: 900, display: "inline-block",
              boxShadow: `0 0 60px ${neon}44, 0 0 120px ${neon}18`,
            }}>
              COMPRAR AGORA
            </div>
          </div>

          <div style={{ opacity: urgOp, marginTop: 28, display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
            <GlassPanel blur={12} opacity={0.12} borderRadius={12} padding="10px 24px" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: 5, background: "#dc2626", opacity: blink }} />
              <span style={{ color: "#fca5a5", fontSize: 36, fontFamily: "monospace" }}>23 unidades</span>
            </GlassPanel>
            <span style={{ fontSize: 36, color: gray }}>Frete gratis | 12x sem juros</span>
          </div>
        </div>
      </div>
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};

// Vertical composition with circular reveals
export const EcommerceV4V: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={100}>
      <CircularReveal durationInFrames={100} transitionFrames={12}><Scene1V /></CircularReveal>
    </Sequence>
    <Sequence from={95} durationInFrames={100}>
      <CircularReveal durationInFrames={100} originX="50%" originY="30%"><Scene2V /></CircularReveal>
    </Sequence>
    <Sequence from={190} durationInFrames={105}>
      <CircularReveal durationInFrames={105} originX="50%" originY="60%"><Scene3V /></CircularReveal>
    </Sequence>
  </AbsoluteFill>
);
