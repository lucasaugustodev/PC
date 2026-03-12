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

const bg = "#0c0c0c";
const orange = "#ff6b2b";
const cyan = "#22d3ee";
const white = "#fafafa";
const gray = "#a1a1aa";
const dark = "#1a1a1a";

// ── CENA 1: Attention Hook with Photo ──
const HookScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Photo enters from right
  const photoX = interpolate(frame, [0, 20], [100, 0], { extrapolateRight: "clamp" });
  const photoOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const photoFloat = Math.sin(frame * 0.07) * 6;

  const textOp = interpolate(frame, [5, 20], [0, 1], { extrapolateRight: "clamp" });
  const priceStrike = interpolate(frame, [30, 35], [0, 1], { extrapolateRight: "clamp" });
  const shakeX = frame > 30 && frame < 42 ? Math.sin(frame * 2.5) * 4 : 0;
  const revealOp = interpolate(frame, [42, 58], [0, 1], { extrapolateRight: "clamp" });
  const revealScale = spring({ frame: Math.max(0, frame - 42), fps, config: { damping: 10 } });

  return (
    <AbsoluteFill style={{ background: bg }}>
      {/* Glow */}
      <div style={{ position: "absolute", top: "30%", right: "15%", width: 500, height: 500, borderRadius: "50%", background: `radial-gradient(circle, ${orange}0c, transparent 60%)` }} />

      <div style={{ display: "flex", height: "100%", alignItems: "center", zIndex: 1, position: "relative" }}>
        {/* Left - Text hook */}
        <div style={{ flex: 1, padding: "0 0 0 100px" }}>
          <div style={{ opacity: textOp }}>
            <div style={{ fontSize: 42, color: gray, fontFamily: "system-ui" }}>Você ainda paga</div>
            <div style={{
              fontSize: 110, fontWeight: 900, color: "#ef4444", fontFamily: "system-ui",
              position: "relative", display: "inline-block",
              transform: `translateX(${shakeX}px)`,
            }}>
              R$ 300+
              <div style={{
                position: "absolute", top: "50%", left: -10, right: -10,
                height: 7, background: "#ef4444", borderRadius: 4,
                transform: "translateY(-50%) rotate(-3deg)",
                opacity: priceStrike,
              }} />
            </div>
            <div style={{ fontSize: 42, color: gray, fontFamily: "system-ui" }}>em fones?</div>
          </div>

          <div style={{ opacity: revealOp, transform: `scale(${revealScale})`, marginTop: 40 }}>
            <div style={{ fontSize: 24, color: orange, letterSpacing: 4, marginBottom: 8 }}>DESCUBRA POR</div>
            <div style={{ fontSize: 96, fontWeight: 900, color: white, fontFamily: "system-ui" }}>
              R$ 79<span style={{ fontSize: 48, color: orange }}>,90</span>
            </div>
          </div>
        </div>

        {/* Right - Product photo */}
        <div style={{ flex: 0.8, display: "flex", justifyContent: "center", alignItems: "center" }}>
          <div style={{
            opacity: photoOp,
            transform: `translateX(${photoX}px) translateY(${photoFloat}px)`,
            width: 480, height: 480,
            borderRadius: 24,
            overflow: "hidden",
            border: `2px solid ${orange}33`,
            boxShadow: `0 20px 60px rgba(0,0,0,0.5), 0 0 40px ${orange}10`,
          }}>
            <Img src={staticFile("img/headphone3.jpg")} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── CENA 2: Multi-angle showcase ──
const ShowcaseScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const angles = [
    { src: "img/headphone1.jpg", label: "Design Premium" },
    { src: "img/headphone2.jpg", label: "Conforto Total" },
    { src: "img/headphone3.jpg", label: "Acabamento Pro" },
  ];

  const features = [
    { title: "ANC Ativo", value: "98%", color: orange },
    { title: "Bateria", value: "48h", color: cyan },
    { title: "Bluetooth", value: "5.3", color: orange },
    { title: "Driver", value: "40mm", color: cyan },
  ];

  return (
    <AbsoluteFill style={{ background: bg }}>
      <div style={{ padding: "50px 60px", height: "100%", display: "flex", flexDirection: "column" }}>
        {/* Top - Photo strip */}
        <div style={{ display: "flex", gap: 20, flex: 1 }}>
          {angles.map((a, i) => {
            const delay = i * 8;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const zoom = interpolate(frame, [delay, delay + 90], [1.1, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                flex: 1, borderRadius: 18, overflow: "hidden",
                transform: `scale(${s})`,
                border: `1px solid #333`,
                position: "relative",
              }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(a.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
                <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "30px 16px 14px", background: "linear-gradient(transparent, rgba(0,0,0,0.8))" }}>
                  <span style={{ fontSize: 18, color: white, fontWeight: 600 }}>{a.label}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom - Feature bar */}
        <div style={{ display: "flex", gap: 16, marginTop: 24 }}>
          {features.map((f, i) => {
            const delay = i * 4 + 20;
            const op = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                opacity: op, flex: 1,
                background: dark, borderRadius: 14,
                border: `1px solid ${f.color}22`,
                padding: "20px 16px", textAlign: "center",
              }}>
                <div style={{ fontSize: 36, fontWeight: 900, color: f.color, fontFamily: "system-ui" }}>{f.value}</div>
                <div style={{ fontSize: 15, color: gray, marginTop: 4 }}>{f.title}</div>
              </div>
            );
          })}

          {/* Review card */}
          <div style={{
            opacity: interpolate(frame, [45, 60], [0, 1], { extrapolateRight: "clamp" }),
            flex: 2, background: dark, borderRadius: 14,
            border: "1px solid #ffffff08", padding: "20px 24px",
            display: "flex", flexDirection: "column", justifyContent: "center",
          }}>
            <div style={{ color: "#fbbf24", fontSize: 18 }}>* * * * *</div>
            <div style={{ fontSize: 15, color: gray, marginTop: 6, fontStyle: "italic" }}>
              "Chegou em 4 dias, qualidade absurda pelo preco" — Pedro L.
            </div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── CENA 3: Urgency CTA ──
const UrgencyCTA: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const zoom = interpolate(frame, [0, 90], [1.15, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 10 } });
  const op = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: "clamp" });
  const btnScale = spring({ frame: Math.max(0, frame - 18), fps, config: { damping: 8 } });
  const pulse = Math.sin(frame * 0.2) * 0.04 + 1;
  const urgOp = interpolate(frame, [30, 42], [0, 1], { extrapolateRight: "clamp" });
  const blink = Math.sin(frame * 0.3) > 0 ? 1 : 0.3;
  const secs = Math.max(0, 59 - Math.floor(frame / 2));

  return (
    <AbsoluteFill>
      {/* Background photo blurred */}
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})`, filter: "blur(25px) brightness(0.25)" }}>
        <Img src={staticFile("img/headphone1.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(12,12,12,0.5)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          {/* Timer */}
          <div style={{ opacity: urgOp, marginBottom: 24, display: "flex", justifyContent: "center", gap: 12 }}>
            {[{ v: "00", l: "DIAS" }, { v: "14", l: "HRS" }, { v: `${secs}`, l: "MIN" }].map((t, i) => (
              <div key={i} style={{ background: dark, border: `1px solid ${orange}44`, borderRadius: 12, padding: "12px 22px", minWidth: 80, textAlign: "center" }}>
                <div style={{ fontSize: 32, fontWeight: 900, color: white, fontFamily: "monospace", opacity: blink }}>{t.v}</div>
                <div style={{ fontSize: 11, color: gray, marginTop: 2 }}>{t.l}</div>
              </div>
            ))}
          </div>

          <div style={{ fontSize: 24, color: orange, letterSpacing: 5, marginBottom: 10 }}>ÚLTIMAS UNIDADES</div>
          <div style={{ fontSize: 66, fontWeight: 900, color: white, fontFamily: "system-ui" }}>SoundPro X1</div>

          <div style={{ display: "flex", justifyContent: "center", alignItems: "baseline", gap: 16, marginTop: 12 }}>
            <span style={{ fontSize: 28, color: gray, textDecoration: "line-through" }}>R$ 329,90</span>
            <span style={{ fontSize: 76, fontWeight: 900, color: orange, fontFamily: "system-ui" }}>R$ 79,90</span>
          </div>
          <div style={{ fontSize: 20, color: cyan, marginTop: 4 }}>76% OFF + Frete Gratis</div>

          <div style={{ transform: `scale(${btnScale * pulse})`, marginTop: 32 }}>
            <div style={{
              background: `linear-gradient(135deg, ${orange}, #e55a1b)`,
              color: white, padding: "22px 80px", borderRadius: 16,
              fontSize: 30, fontWeight: 900, display: "inline-block",
              fontFamily: "system-ui",
              boxShadow: `0 0 50px ${orange}44`,
            }}>
              GARANTIR O MEU
            </div>
          </div>

          <div style={{ opacity: urgOp, marginTop: 18, fontSize: 14, color: gray }}>
            Garantia 30 dias | Entrega 3-7 dias | Pix, Cartao, Boleto
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const DemoDropshipping: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={90}><HookScene /></Sequence>
    <Sequence from={90} durationInFrames={90}><ShowcaseScene /></Sequence>
    <Sequence from={180} durationInFrames={90}><UrgencyCTA /></Sequence>
  </AbsoluteFill>
);
