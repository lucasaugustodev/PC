import React from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Sequence,
  Img,
  Audio,
  staticFile,
} from "remotion";

const gold = "#d4a853";
const white = "#f8fafc";
const gray = "#94a3b8";
const dark = "#0f172a";

// ── CENA 1: Cinematic Photo Hero ──
const CinematicHero: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Ken Burns zoom
  const zoom = interpolate(frame, [0, 90], [1.15, 1.02], { extrapolateRight: "clamp" });
  const panX = interpolate(frame, [0, 90], [-3, 2], { extrapolateRight: "clamp" });

  const overlayOp = interpolate(frame, [0, 15], [1, 0.55], { extrapolateRight: "clamp" });
  const titleOp = interpolate(frame, [8, 25], [0, 1], { extrapolateRight: "clamp" });
  const titleY = interpolate(frame, [8, 25], [50, 0], { extrapolateRight: "clamp" });
  const lineW = interpolate(frame, [20, 45], [0, 400], { extrapolateRight: "clamp" });
  const priceOp = interpolate(frame, [30, 45], [0, 1], { extrapolateRight: "clamp" });
  const priceScale = spring({ frame: Math.max(0, frame - 30), fps, config: { damping: 12 } });
  const badgeOp = interpolate(frame, [40, 55], [0, 1], { extrapolateRight: "clamp" });
  const logoOp = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });

  return (
    <AbsoluteFill>
      {/* Photo background with Ken Burns */}
      <div style={{ position: "absolute", inset: -60, transform: `scale(${zoom}) translateX(${panX}%)` }}>
        <Img src={staticFile("img/house1.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>

      {/* Gradient overlay */}
      <div style={{ position: "absolute", inset: 0, background: `linear-gradient(180deg, rgba(15,23,42,${overlayOp}) 0%, rgba(15,23,42,0.85) 60%, rgba(15,23,42,0.95) 100%)` }} />

      {/* Top bar with logo */}
      <div style={{ position: "absolute", top: 40, left: 60, right: 60, display: "flex", justifyContent: "space-between", alignItems: "center", opacity: logoOp, zIndex: 2 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ width: 10, height: 10, background: gold, transform: "rotate(45deg)" }} />
          <span style={{ fontSize: 16, color: gold, letterSpacing: 5, textTransform: "uppercase" }}>Premium Living</span>
        </div>
        <span style={{ fontSize: 14, color: gray }}>CRECI 54321-J</span>
      </div>

      {/* Main content - bottom aligned */}
      <div style={{ position: "absolute", bottom: 80, left: 80, right: 80, zIndex: 2 }}>
        <div style={{ opacity: titleOp, transform: `translateY(${titleY}px)` }}>
          <div style={{ fontSize: 22, color: gold, letterSpacing: 6, marginBottom: 12 }}>EXCLUSIVO</div>
          <div style={{ fontSize: 82, fontWeight: 800, color: white, fontFamily: "system-ui", lineHeight: 1.05 }}>
            Cobertura Duplex
          </div>
          <div style={{ fontSize: 34, color: gray, marginTop: 8 }}>Jardins, São Paulo - SP</div>
        </div>

        <div style={{ width: lineW, height: 2, background: `linear-gradient(90deg, ${gold}, transparent)`, marginTop: 24 }} />

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginTop: 24 }}>
          {/* Price */}
          <div style={{ opacity: priceOp, transform: `scale(${priceScale})` }}>
            <div style={{ fontSize: 18, color: gold, letterSpacing: 3, marginBottom: 4 }}>A PARTIR DE</div>
            <div style={{ fontSize: 72, fontWeight: 900, color: white, fontFamily: "system-ui" }}>
              R$ 2.8<span style={{ fontSize: 42, color: gold }}>M</span>
            </div>
          </div>

          {/* Feature badges */}
          <div style={{ opacity: badgeOp, display: "flex", gap: 14 }}>
            {[
              { n: "380", u: "m2" },
              { n: "4", u: "suites" },
              { n: "6", u: "vagas" },
              { n: "2", u: "andares" },
            ].map((b, i) => (
              <div key={i} style={{
                background: "rgba(212,168,83,0.1)",
                border: `1px solid ${gold}44`,
                borderRadius: 12,
                padding: "14px 20px",
                textAlign: "center",
                backdropFilter: "blur(10px)",
              }}>
                <div style={{ fontSize: 28, fontWeight: 800, color: white }}>{b.n}</div>
                <div style={{ fontSize: 13, color: gold, marginTop: 2 }}>{b.u}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── CENA 2: Photo Gallery + Features ──
const GalleryScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const photos = [
    { src: "img/house2.jpg", label: "Living Room" },
    { src: "img/house3.jpg", label: "Vista Panorâmica" },
  ];

  const features = [
    "Piso em mármore importado",
    "Automacao completa",
    "Spa e sauna privativa",
    "Adega climatizada",
    "Home theater",
    "Churrasqueira gourmet",
  ];

  return (
    <AbsoluteFill style={{ background: dark }}>
      <div style={{ display: "flex", height: "100%" }}>
        {/* Left - Photos stacked */}
        <div style={{ flex: 1.2, padding: 40, display: "flex", flexDirection: "column", gap: 20 }}>
          {photos.map((photo, i) => {
            const delay = i * 10;
            const s = spring({ frame: Math.max(0, frame - delay), fps, config: { damping: 14 } });
            const zoom = interpolate(frame, [delay, delay + 90], [1.08, 1], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                flex: 1,
                borderRadius: 16,
                overflow: "hidden",
                transform: `scale(${s})`,
                position: "relative",
              }}>
                <div style={{ position: "absolute", inset: 0, transform: `scale(${zoom})` }}>
                  <Img src={staticFile(photo.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                </div>
                <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, padding: "40px 20px 16px", background: "linear-gradient(transparent, rgba(0,0,0,0.7))" }}>
                  <span style={{ fontSize: 16, color: white, fontFamily: "system-ui" }}>{photo.label}</span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Right - Features list */}
        <div style={{ flex: 0.8, padding: "60px 50px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <div style={{ fontSize: 18, color: gold, letterSpacing: 4, marginBottom: 8 }}>DIFERENCIAIS</div>
          <div style={{ fontSize: 42, fontWeight: 700, color: white, fontFamily: "system-ui", marginBottom: 36 }}>
            Cada Detalhe<br />Pensado Para<br /><span style={{ color: gold }}>Voce</span>
          </div>

          {features.map((f, i) => {
            const delay = i * 4 + 10;
            const op = interpolate(frame, [delay, delay + 10], [0, 1], { extrapolateRight: "clamp" });
            const x = interpolate(frame, [delay, delay + 10], [30, 0], { extrapolateRight: "clamp" });
            return (
              <div key={i} style={{
                opacity: op,
                transform: `translateX(${x}px)`,
                display: "flex",
                alignItems: "center",
                gap: 14,
                marginBottom: 18,
              }}>
                <div style={{ width: 6, height: 6, background: gold, borderRadius: 1, transform: "rotate(45deg)", flexShrink: 0 }} />
                <span style={{ fontSize: 20, color: gray }}>{f}</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// ── CENA 3: CTA com foto de fundo ──
const CTAScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const zoom = interpolate(frame, [0, 90], [1.1, 1], { extrapolateRight: "clamp" });
  const scale = spring({ frame, fps, config: { damping: 12 } });
  const op = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  const lineW = interpolate(frame, [15, 40], [0, 500], { extrapolateRight: "clamp" });
  const ctaOp = interpolate(frame, [30, 45], [0, 1], { extrapolateRight: "clamp" });
  const ctaScale = spring({ frame: Math.max(0, frame - 30), fps, config: { damping: 8 } });
  const pulse = Math.sin(frame * 0.15) * 0.03 + 1;

  return (
    <AbsoluteFill>
      {/* Background photo */}
      <div style={{ position: "absolute", inset: -40, transform: `scale(${zoom})` }}>
        <Img src={staticFile("img/house1.jpg")} style={{ width: "110%", height: "110%", objectFit: "cover" }} />
      </div>
      <div style={{ position: "absolute", inset: 0, background: "rgba(15,23,42,0.82)" }} />

      <div style={{ position: "absolute", inset: 0, display: "flex", justifyContent: "center", alignItems: "center", zIndex: 1 }}>
        <div style={{ transform: `scale(${scale})`, opacity: op, textAlign: "center" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, justifyContent: "center", marginBottom: 20 }}>
            <div style={{ width: 8, height: 8, background: gold, transform: "rotate(45deg)" }} />
            <span style={{ fontSize: 16, color: gold, letterSpacing: 5 }}>PREMIUM LIVING</span>
            <div style={{ width: 8, height: 8, background: gold, transform: "rotate(45deg)" }} />
          </div>

          <div style={{ fontSize: 60, fontWeight: 800, color: white, fontFamily: "system-ui", lineHeight: 1.15 }}>
            Agende Sua<br />
            <span style={{ color: gold }}>Visita Exclusiva</span>
          </div>

          <div style={{ width: lineW, height: 2, background: `linear-gradient(90deg, transparent, ${gold}, transparent)`, margin: "28px auto" }} />

          <div style={{ opacity: ctaOp, transform: `scale(${ctaScale * pulse})`, marginTop: 20 }}>
            <div style={{
              background: `linear-gradient(135deg, ${gold}, #b8922e)`,
              color: dark,
              padding: "22px 70px",
              borderRadius: 14,
              fontSize: 32,
              fontWeight: 800,
              display: "inline-block",
              fontFamily: "system-ui",
              boxShadow: `0 0 60px ${gold}33`,
            }}>
              (11) 99999-0000
            </div>
          </div>

          <div style={{ opacity: ctaOp, marginTop: 24, display: "flex", gap: 30, justifyContent: "center" }}>
            <span style={{ fontSize: 17, color: gray }}>@premiumliving</span>
            <span style={{ fontSize: 17, color: gray }}>premiumliving.com.br</span>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

export const DemoImobiliaria: React.FC = () => (
  <AbsoluteFill>
    <Sequence from={0} durationInFrames={90}><CinematicHero /></Sequence>
    <Sequence from={90} durationInFrames={90}><GalleryScene /></Sequence>
    <Sequence from={180} durationInFrames={90}><CTAScene /></Sequence>
  </AbsoluteFill>
);
