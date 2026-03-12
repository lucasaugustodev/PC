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
import { Animated, Fade, Move, Scale } from "remotion-animated";
import {
  CircularReveal,
  GlassPanel,
  FilmGrain,
  AnimatedCounter,
} from "./Transitions";

// ── Design tokens ──
const bg = "#0a0a0a";
const neon = "#00ff88";
const purple = "#a855f7";
const pink = "#ec4899";
const white = "#fafafa";
const gray = "#a1a1aa";

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

// ── Floating photo with parallax + shine (visible from frame 0) ──
const FloatingPhoto: React.FC<{
  src: string;
  size: number;
  borderColor?: string;
}> = ({ src, size, borderColor = neon }) => {
  const frame = useCurrentFrame();
  const floatY = Math.sin(frame * 0.06) * 12;
  const floatRotate = Math.sin(frame * 0.04) * 2;
  const shineAngle = 120 + frame * 0.5;

  return (
    <Animated
      animations={[
        Scale({ by: 1, initial: 0.85, start: 0, duration: 18 }),
        Fade({ to: 1, initial: 0, start: 0, duration: 8 }),
      ]}
    >
      <div style={{
        transform: `translateY(${floatY}px) rotate(${floatRotate}deg)`,
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
    </Animated>
  );
};

// ── Pulsing CTA button ──
const PulsingCTA: React.FC<{ text: string; startFrame: number }> = ({ text, startFrame }) => {
  const frame = useCurrentFrame();
  const pulse = Math.sin(frame * 0.18) * 0.04 + 1;
  const glowIntensity = 40 + Math.sin(frame * 0.15) * 20;

  return (
    <Animated
      animations={[
        Scale({ by: 1, initial: 0, start: startFrame, duration: 20 }),
        Fade({ to: 1, initial: 0, start: startFrame, duration: 10 }),
      ]}
    >
      <div style={{ transform: `scale(${pulse})` }}>
        <div style={{
          background: `linear-gradient(135deg, ${neon}, #00cc6a)`,
          color: bg, padding: "24px 90px", borderRadius: 18,
          fontSize: 44, fontWeight: 900, display: "inline-block",
          fontFamily: "system-ui",
          boxShadow: `0 0 ${glowIntensity}px ${neon}66, 0 0 ${glowIntensity * 2}px ${neon}22`,
          transition: "box-shadow 0.1s",
        }}>
          {text}
        </div>
      </div>
    </Animated>
  );
};

// ════════════════════════════════════════
// HORIZONTAL (1920x1080) — 450 frames = 15s
// ════════════════════════════════════════

const Scene1H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const priceOp = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const priceY = spring({ frame: Math.max(0, frame - 40), fps, config: { damping: 12, stiffness: 100 } });

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg />
      <div style={{ display: "flex", height: "100%", alignItems: "center", zIndex: 1, position: "relative", padding: "0 80px" }}>
        {/* Left - Product visible immediately */}
        <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
          <FloatingPhoto src="img/headphone1.jpg" size={500} />
        </div>

        {/* Right - Info */}
        <div style={{ flex: 1 }}>
          {/* Badge */}
          <Animated animations={[
            Scale({ by: 1, initial: 0, start: 0, duration: 15 }),
            Fade({ to: 1, initial: 0, start: 0, duration: 8 }),
          ]}>
            <div style={{ display: "inline-block", background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "10px 28px", borderRadius: 24, fontSize: 36, fontWeight: 800, marginBottom: 32 }}>
              -40% OFF
            </div>
          </Animated>

          {/* Title - slam in */}
          <Animated animations={[
            Scale({ by: 1, initial: 2.5, start: 3, duration: 14 }),
            Fade({ to: 1, initial: 0, start: 3, duration: 6 }),
          ]}>
            <div style={{ fontSize: 88, fontWeight: 900, color: white, fontFamily: "system-ui", textShadow: "0 4px 30px rgba(0,0,0,0.5)" }}>
              Fone Bluetooth
            </div>
          </Animated>

          <Animated animations={[
            Scale({ by: 1, initial: 2.5, start: 10, duration: 14 }),
            Fade({ to: 1, initial: 0, start: 10, duration: 6 }),
          ]}>
            <div style={{ fontSize: 88, fontWeight: 900, color: neon, fontFamily: "system-ui", textShadow: `0 4px 40px ${neon}33` }}>
              Pro Max X1
            </div>
          </Animated>

          {/* Features in glass panel */}
          <Animated animations={[
            Move({ y: 0, initialY: 30, start: 25, duration: 18 }),
            Fade({ to: 1, initial: 0, start: 25, duration: 12 }),
          ]}>
            <GlassPanel blur={20} opacity={0.08} borderRadius={16} padding="24px 32px" style={{ marginTop: 28 }}>
              <div style={{ fontSize: 40, color: gray, lineHeight: 1.6 }}>
                Cancelamento de ruído ativo<br />48h bateria | Bluetooth 5.3
              </div>
            </GlassPanel>
          </Animated>

          {/* Price */}
          <div style={{ opacity: priceOp, marginTop: 28, transform: `translateY(${(1 - priceY) * 30}px)` }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
              <span style={{ fontSize: 48, color: gray, textDecoration: "line-through" }}>R$ 329</span>
              <span style={{ fontSize: 96, fontWeight: 900, color: white, fontFamily: "system-ui" }}>R$</span>
              <AnimatedCounter to={199} startFrame={42} duration={18} fontSize={96} color={white} />
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
    { t: "48h Bateria", d: "Carga rápida", c: purple },
    { t: "BT 5.3", d: "15m alcance", c: pink },
    { t: "IPX7", d: "À prova d'água", c: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg color1={purple} color2={pink} />
      <div style={{ display: "flex", height: "100%", zIndex: 1, position: "relative", padding: "40px 80px" }}>
        {/* Left - Photo grid with Ken Burns */}
        <div style={{ flex: 0.9, display: "flex", gap: 16 }}>
          {photos.map((src, i) => {
            const delay = i * 8;
            const zoom = interpolate(frame, [delay, delay + 120], [1.12, 1], { extrapolateRight: "clamp" });
            const isMain = i === 1;
            return (
              <Animated key={i} animations={[
                Scale({ by: 1, initial: 0.8, start: delay, duration: 18 }),
                Fade({ to: 1, initial: 0, start: delay, duration: 10 }),
              ]} style={{ flex: isMain ? 2.2 : 1, borderRadius: 20, overflow: "hidden", border: isMain ? `2px solid ${neon}44` : "1px solid #333", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              </Animated>
            );
          })}
        </div>

        {/* Right - Stats + Features */}
        <div style={{ flex: 1.1, paddingLeft: 40, display: "flex", flexDirection: "column", justifyContent: "center" }}>
          {/* Stats in glass panels */}
          <div style={{ display: "flex", gap: 16, marginBottom: 28 }}>
            {[
              { to: 4.8, label: "Avaliação", decimals: 1, suffix: "" },
              { to: 50, label: "Mil vendidos", decimals: 0, suffix: "K+" },
            ].map((s, i) => {
              const delay = i * 8 + 10;
              return (
                <Animated key={i} animations={[
                  Scale({ by: 1, initial: 0, start: delay, duration: 16 }),
                  Fade({ to: 1, initial: 0, start: delay, duration: 10 }),
                ]} style={{ flex: 1 }}>
                  <GlassPanel blur={20} opacity={0.1} borderRadius={16} padding="24px 20px" style={{ textAlign: "center" }}>
                    <AnimatedCounter to={s.to} startFrame={delay + 6} duration={18} fontSize={56} color={neon} decimals={s.decimals} suffix={s.suffix} />
                    <div style={{ fontSize: 36, color: white, marginTop: 6 }}>{s.label}</div>
                  </GlassPanel>
                </Animated>
              );
            })}
          </div>

          {/* Features with slide-in */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 14 }}>
            {features.map((f, i) => {
              const delay = i * 5 + 28;
              return (
                <Animated key={i} animations={[
                  Move({ x: 0, initialX: 60, start: delay, duration: 16 }),
                  Fade({ to: 1, initial: 0, start: delay, duration: 10 }),
                ]} style={{ width: 240 }}>
                  <GlassPanel blur={16} opacity={0.08} borderRadius={14} padding="18px 22px" style={{ borderLeft: `4px solid ${f.c}` }}>
                    <div style={{ fontSize: 40, fontWeight: 700, color: white }}>{f.t}</div>
                    <div style={{ fontSize: 36, color: gray, marginTop: 4 }}>{f.d}</div>
                  </GlassPanel>
                </Animated>
              );
            })}
          </div>

          {/* Review */}
          <Animated animations={[
            Move({ y: 0, initialY: 20, start: 55, duration: 16 }),
            Fade({ to: 1, initial: 0, start: 55, duration: 12 }),
          ]}>
            <GlassPanel blur={16} opacity={0.06} borderRadius={14} padding="18px 22px" style={{ marginTop: 16 }}>
              <span style={{ color: "#fbbf24", fontSize: 40 }}>*****</span>
              <span style={{ fontSize: 36, color: gray, marginLeft: 14 }}>"Melhor custo-benefício" — Ana M.</span>
            </GlassPanel>
          </Animated>
        </div>
      </div>
      <FilmGrain />
    </AbsoluteFill>
  );
};

const Scene3H: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const zoom = interpolate(frame, [0, 120], [1.1, 1], { extrapolateRight: "clamp" });
  const urgOp = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      {/* Blurred photo bg with parallax */}
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(30px) brightness(0.22)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.5)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1 }}>
        <div style={{ textAlign: "center" }}>
          <Animated animations={[
            Fade({ to: 1, initial: 0, start: 0, duration: 10 }),
            Move({ y: 0, initialY: -20, start: 0, duration: 14 }),
          ]}>
            <div style={{ fontSize: 44, color: neon, letterSpacing: 6, marginBottom: 16 }}>OFERTA RELÂMPAGO</div>
          </Animated>

          {/* Product name slams in */}
          <Animated animations={[
            Scale({ by: 1, initial: 3, start: 5, duration: 14 }),
            Fade({ to: 1, initial: 0, start: 5, duration: 6 }),
          ]}>
            <div style={{ fontSize: 110, fontWeight: 900, color: white, fontFamily: "system-ui", textShadow: "0 4px 40px rgba(0,0,0,0.5)" }}>
              Pro Max X1
            </div>
          </Animated>

          {/* Price */}
          <Animated animations={[
            Move({ y: 0, initialY: 40, start: 18, duration: 16 }),
            Fade({ to: 1, initial: 0, start: 18, duration: 10 }),
          ]}>
            <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, marginTop: 20 }}>
              <span style={{ fontSize: 44, color: gray, textDecoration: "line-through" }}>R$ 329</span>
              <span style={{ fontSize: 110, fontWeight: 900, color: neon, fontFamily: "system-ui" }}>R$</span>
              <AnimatedCounter to={199} startFrame={20} duration={16} fontSize={110} color={neon} />
              <span style={{ fontSize: 52, color: neon }}>,90</span>
            </div>
          </Animated>

          {/* CTA button with pulse + glow */}
          <div style={{ marginTop: 40 }}>
            <PulsingCTA text="COMPRAR AGORA" startFrame={30} />
          </div>

          {/* Urgency */}
          <div style={{ opacity: urgOp, marginTop: 28, display: "flex", gap: 16, justifyContent: "center", alignItems: "center" }}>
            <GlassPanel blur={12} opacity={0.12} borderRadius={12} padding="10px 24px" style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 10, height: 10, borderRadius: 5, background: "#dc2626", opacity: blink }} />
              <span style={{ color: "#fca5a5", fontSize: 36, fontFamily: "monospace" }}>23 unidades</span>
            </GlassPanel>
            <span style={{ fontSize: 36, color: gray }}>Frete grátis</span>
          </div>
        </div>
      </div>
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};

// Horizontal: 3 scenes, 150 frames each = 15s at 30fps
export const EcommerceV4H: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={155}>
      <CircularReveal durationInFrames={155} transitionFrames={12}><Scene1H /></CircularReveal>
    </Sequence>
    <Sequence from={148} durationInFrames={155}>
      <CircularReveal durationInFrames={155} originX="30%" originY="40%"><Scene2H /></CircularReveal>
    </Sequence>
    <Sequence from={296} durationInFrames={160}>
      <CircularReveal durationInFrames={160} originX="50%" originY="60%"><Scene3H /></CircularReveal>
    </Sequence>
  </AbsoluteFill>
);

// ════════════════════════════════════════
// VERTICAL (1080x1920) — Safe zone: center 900x1492
// ════════════════════════════════════════

const Scene1V: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const priceOp = interpolate(frame, [44, 58], [0, 1], { extrapolateRight: "clamp" });
  const priceY = spring({ frame: Math.max(0, frame - 44), fps, config: { damping: 12 } });

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg />
      <div style={{ display: "flex", flexDirection: "column", height: "100%", alignItems: "center", justifyContent: "center", padding: "214px 90px", zIndex: 1 }}>
        {/* Badge */}
        <Animated animations={[
          Scale({ by: 1, initial: 0, start: 0, duration: 15 }),
          Fade({ to: 1, initial: 0, start: 0, duration: 8 }),
        ]}>
          <div style={{ background: `linear-gradient(135deg, ${neon}, #00cc6a)`, color: bg, padding: "10px 28px", borderRadius: 24, fontSize: 36, fontWeight: 800, marginBottom: 32 }}>
            -40% OFF
          </div>
        </Animated>

        {/* Product photo - visible immediately */}
        <FloatingPhoto src="img/headphone1.jpg" size={420} />

        {/* Title slam */}
        <div style={{ marginTop: 36, textAlign: "center" }}>
          <Animated animations={[
            Scale({ by: 1, initial: 2.5, start: 6, duration: 14 }),
            Fade({ to: 1, initial: 0, start: 6, duration: 6 }),
          ]}>
            <div style={{ fontSize: 72, fontWeight: 900, color: white, fontFamily: "system-ui", textShadow: "0 4px 30px rgba(0,0,0,0.5)" }}>Fone Pro</div>
          </Animated>
          <Animated animations={[
            Scale({ by: 1, initial: 2.5, start: 12, duration: 14 }),
            Fade({ to: 1, initial: 0, start: 12, duration: 6 }),
          ]}>
            <div style={{ fontSize: 72, fontWeight: 900, color: neon, fontFamily: "system-ui", textShadow: `0 4px 40px ${neon}33` }}>Max X1</div>
          </Animated>
        </div>

        {/* Features */}
        <Animated animations={[
          Move({ y: 0, initialY: 20, start: 28, duration: 16 }),
          Fade({ to: 1, initial: 0, start: 28, duration: 10 }),
        ]}>
          <GlassPanel blur={20} opacity={0.08} borderRadius={16} padding="20px 28px" style={{ marginTop: 24, textAlign: "center" }}>
            <div style={{ fontSize: 40, color: gray, lineHeight: 1.5 }}>
              ANC | 48h | BT 5.3 | IPX7
            </div>
          </GlassPanel>
        </Animated>

        {/* Price */}
        <div style={{ opacity: priceOp, marginTop: 28, textAlign: "center", transform: `translateY(${(1 - priceY) * 25}px)` }}>
          <span style={{ fontSize: 40, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
          <div style={{ display: "flex", alignItems: "baseline", gap: 8, justifyContent: "center", marginTop: 8 }}>
            <span style={{ fontSize: 80, fontWeight: 900, color: white, fontFamily: "system-ui" }}>R$</span>
            <AnimatedCounter to={199} startFrame={46} duration={16} fontSize={80} color={white} />
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
    { t: "48h Bateria", d: "Rápida", c: purple },
    { t: "BT 5.3", d: "15m", c: pink },
    { t: "IPX7", d: "Água", c: neon },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <GlowBg color1={purple} color2={pink} />
      <div style={{ padding: "214px 90px", display: "flex", flexDirection: "column", height: "100%", zIndex: 1, position: "relative" }}>
        {/* Photo strip */}
        <div style={{ display: "flex", gap: 12, height: 320 }}>
          {photos.map((src, i) => {
            const delay = i * 6;
            const zoom = interpolate(frame, [delay, delay + 100], [1.1, 1], { extrapolateRight: "clamp" });
            return (
              <Animated key={i} animations={[
                Scale({ by: 1, initial: 0.8, start: delay, duration: 16 }),
                Fade({ to: 1, initial: 0, start: delay, duration: 10 }),
              ]} style={{ flex: i === 1 ? 1.8 : 1, borderRadius: 16, overflow: "hidden", border: i === 1 ? `2px solid ${neon}44` : "1px solid #333", position: "relative" }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
              </Animated>
            );
          })}
        </div>

        {/* Stats */}
        <div style={{ display: "flex", gap: 14, marginTop: 24 }}>
          {[
            { to: 4.8, l: "Nota", d: 1, s: "" },
            { to: 50, l: "Mil vendas", d: 0, s: "K+" },
          ].map((st, i) => {
            const delay = i * 6 + 14;
            return (
              <Animated key={i} animations={[
                Scale({ by: 1, initial: 0, start: delay, duration: 16 }),
                Fade({ to: 1, initial: 0, start: delay, duration: 10 }),
              ]} style={{ flex: 1 }}>
                <GlassPanel blur={16} opacity={0.1} borderRadius={14} padding="20px 16px" style={{ textAlign: "center" }}>
                  <AnimatedCounter to={st.to} startFrame={delay + 4} duration={16} fontSize={48} color={neon} decimals={st.d} suffix={st.s} />
                  <div style={{ fontSize: 36, color: gray, marginTop: 4 }}>{st.l}</div>
                </GlassPanel>
              </Animated>
            );
          })}
        </div>

        {/* Features grid */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 12, marginTop: 20, flex: 1, alignContent: "center" }}>
          {features.map((f, i) => {
            const delay = i * 4 + 28;
            return (
              <Animated key={i} animations={[
                Move({ x: 0, initialX: 40, start: delay, duration: 14 }),
                Fade({ to: 1, initial: 0, start: delay, duration: 10 }),
              ]} style={{ flex: "1 1 40%" }}>
                <GlassPanel blur={14} opacity={0.08} borderRadius={12} padding="16px 20px" style={{ borderLeft: `4px solid ${f.c}` }}>
                  <div style={{ fontSize: 40, fontWeight: 700, color: white }}>{f.t}</div>
                  <div style={{ fontSize: 36, color: gray, marginTop: 2 }}>{f.d}</div>
                </GlassPanel>
              </Animated>
            );
          })}
        </div>

        {/* Review */}
        <Animated animations={[
          Move({ y: 0, initialY: 20, start: 55, duration: 14 }),
          Fade({ to: 1, initial: 0, start: 55, duration: 10 }),
        ]}>
          <GlassPanel blur={14} opacity={0.06} borderRadius={12} padding="16px 20px" style={{ marginTop: 12 }}>
            <span style={{ color: "#fbbf24", fontSize: 36 }}>*****</span>
            <span style={{ fontSize: 36, color: gray, marginLeft: 10 }}>"Qualidade absurda" — Pedro</span>
          </GlassPanel>
        </Animated>
      </div>
      <FilmGrain />
    </AbsoluteFill>
  );
};

const Scene3V: React.FC = () => {
  const frame = useCurrentFrame();
  const zoom = interpolate(frame, [0, 120], [1.12, 1], { extrapolateRight: "clamp" });
  const urgOp = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.4;

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(30px) brightness(0.2)" }}>
        <Img src={staticFile("img/headphone2.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(10,10,10,0.45)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", padding: "214px 90px", zIndex: 1 }}>
        <Animated animations={[
          Fade({ to: 1, initial: 0, start: 0, duration: 10 }),
          Move({ y: 0, initialY: -20, start: 0, duration: 14 }),
        ]}>
          <div style={{ fontSize: 40, color: neon, letterSpacing: 6, marginBottom: 20, textAlign: "center" }}>OFERTA RELÂMPAGO</div>
        </Animated>

        <Animated animations={[
          Scale({ by: 1, initial: 3, start: 5, duration: 14 }),
          Fade({ to: 1, initial: 0, start: 5, duration: 6 }),
        ]}>
          <div style={{ fontSize: 80, fontWeight: 900, color: white, fontFamily: "system-ui", textAlign: "center", textShadow: "0 4px 40px rgba(0,0,0,0.5)" }}>Pro Max</div>
        </Animated>
        <Animated animations={[
          Scale({ by: 1, initial: 3, start: 10, duration: 14 }),
          Fade({ to: 1, initial: 0, start: 10, duration: 6 }),
        ]}>
          <div style={{ fontSize: 80, fontWeight: 900, color: neon, fontFamily: "system-ui", textAlign: "center", textShadow: `0 4px 40px ${neon}33` }}>X1</div>
        </Animated>

        <Animated animations={[
          Move({ y: 0, initialY: 40, start: 18, duration: 16 }),
          Fade({ to: 1, initial: 0, start: 18, duration: 10 }),
        ]}>
          <div style={{ textAlign: "center", marginTop: 24 }}>
            <span style={{ fontSize: 40, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8, justifyContent: "center", marginTop: 12 }}>
              <span style={{ fontSize: 96, fontWeight: 900, color: neon, fontFamily: "system-ui" }}>R$</span>
              <AnimatedCounter to={199} startFrame={20} duration={14} fontSize={96} color={neon} />
              <span style={{ fontSize: 48, color: neon }}>,90</span>
            </div>
          </div>
        </Animated>

        <div style={{ marginTop: 40 }}>
          <PulsingCTA text="COMPRAR AGORA" startFrame={30} />
        </div>

        <div style={{ opacity: urgOp, marginTop: 28, display: "flex", flexDirection: "column", gap: 12, alignItems: "center" }}>
          <GlassPanel blur={12} opacity={0.12} borderRadius={12} padding="10px 24px" style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div style={{ width: 10, height: 10, borderRadius: 5, background: "#dc2626", opacity: blink }} />
            <span style={{ color: "#fca5a5", fontSize: 36, fontFamily: "monospace" }}>23 unidades</span>
          </GlassPanel>
          <span style={{ fontSize: 36, color: gray }}>Frete grátis | 12x sem juros</span>
        </div>
      </div>
      <FilmGrain opacity={0.05} />
    </AbsoluteFill>
  );
};

// Vertical: 3 scenes, 150 frames each = 15s
export const EcommerceV4V: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={155}>
      <CircularReveal durationInFrames={155} transitionFrames={12}><Scene1V /></CircularReveal>
    </Sequence>
    <Sequence from={148} durationInFrames={155}>
      <CircularReveal durationInFrames={155} originX="50%" originY="30%"><Scene2V /></CircularReveal>
    </Sequence>
    <Sequence from={296} durationInFrames={160}>
      <CircularReveal durationInFrames={160} originX="50%" originY="60%"><Scene3V /></CircularReveal>
    </Sequence>
  </AbsoluteFill>
);
