"""Generate a proper ambient/corporate music track as WAV."""
import struct, math, wave, os, random

SR = 44100
DURATION = 10
BPM = 105
beat_samples = int(SR * 60 / BPM)

random.seed(42)

def lerp(a, b, t):
    return a + (b - a) * t

def env_adsr(t, a=0.01, d=0.05, s=0.7, r_time=0.3, dur=0.5):
    if t < 0: return 0
    if t < a: return t / a
    if t < a + d: return 1.0 - (1.0 - s) * ((t - a) / d)
    if t < dur - r_time: return s
    if t < dur: return s * (1.0 - (t - (dur - r_time)) / r_time)
    return 0

def soft_saw(phase):
    p = phase % 1.0
    return (2.0 * p - 1.0) * 0.7

def sine(phase):
    return math.sin(2 * math.pi * phase)

# Chord progression: Am - F - C - G (in Hz, root notes)
chords = [
    [220.0, 261.63, 329.63],   # Am
    [174.61, 220.0, 261.63],   # F
    [261.63, 329.63, 392.0],   # C
    [196.0, 246.94, 293.66],   # G
]

samples = []

for i in range(SR * DURATION):
    t = i / SR
    beat = i / beat_samples
    bar = int(beat / 4)
    beat_in_bar = beat % 4
    chord_idx = bar % 4
    chord = chords[chord_idx]

    sample = 0.0

    # === PAD (warm analog pad with slow attack) ===
    pad = 0.0
    for j, freq in enumerate(chord):
        # Detuned for warmth
        phase1 = (freq * t) % 1.0
        phase2 = (freq * 1.003 * t) % 1.0
        # Slow filter-like effect via amplitude modulation
        brightness = 0.3 + 0.15 * math.sin(t * 0.4 + j)
        pad += (sine(phase1) + sine(phase2) * 0.8) * brightness * 0.06
    # Pad envelope per chord change
    chord_t = (beat % 4) * 60 / BPM
    pad_env = min(1.0, chord_t / 0.3) * min(1.0, (4 * 60 / BPM - chord_t) / 0.2)
    pad *= pad_env
    sample += pad

    # === BASS (sub + mid) ===
    bass_freq = chord[0] / 2  # One octave down from root
    bass_phase = (bass_freq * t) % 1.0
    # Sidechain-like pumping
    pump_t = (i % beat_samples) / beat_samples
    pump = 0.5 + 0.5 * min(1.0, pump_t * 4)  # Quick recovery
    bass = sine(bass_phase) * 0.22 * pump
    # Add some mid bass harmonic
    bass += sine(bass_freq * 2 * t % 1.0) * 0.06 * pump
    sample += bass

    # === KICK (every beat) ===
    kick_pos = i % beat_samples
    if kick_pos < int(SR * 0.12):
        kick_t = kick_pos / SR
        kick_freq = 55 + 120 * math.exp(-kick_t * 50)
        kick = sine(kick_freq * kick_t) * math.exp(-kick_t * 18) * 0.4
        sample += kick

    # === HI-HAT (8th notes, alternating velocity) ===
    eighth = beat_samples // 2
    hat_pos = i % eighth
    is_offbeat = (i // eighth) % 2 == 1
    hat_vel = 0.08 if is_offbeat else 0.05
    if hat_pos < int(SR * 0.015):
        hat_t = hat_pos / SR
        hat = 0.0
        for f in [7000, 9500, 12000, 14500]:
            hat += sine(f * hat_t + random.random() * 0.5)
        hat *= math.exp(-hat_t * 200) * hat_vel / 4
        sample += hat

    # === PLUCK (arpeggiated notes on 16th notes, sparse) ===
    sixteenth = beat_samples // 4
    six_pos = i % sixteenth
    six_idx = int(beat * 4) % 16
    # Only play on certain steps for musicality
    play_steps = [0, 3, 5, 8, 10, 13]
    if six_idx in play_steps and six_pos < int(SR * 0.15):
        pluck_t = six_pos / SR
        note_idx = play_steps.index(six_idx) % len(chord)
        pluck_freq = chord[note_idx] * 2  # Octave up
        pluck = sine(pluck_freq * pluck_t) * env_adsr(pluck_t, a=0.002, d=0.03, s=0.3, r_time=0.08, dur=0.15) * 0.1
        # Add a tiny bit of harmonics
        pluck += sine(pluck_freq * 2 * pluck_t) * env_adsr(pluck_t, a=0.001, d=0.02, s=0.1, r_time=0.05, dur=0.1) * 0.03
        sample += pluck

    # === SHAKER (16th notes, very subtle) ===
    if six_pos < int(SR * 0.008):
        shk_t = six_pos / SR
        shaker = sum(sine(f * shk_t + random.random()) for f in [8000, 11000, 15000]) / 3
        shaker *= math.exp(-shk_t * 300) * 0.025
        sample += shaker

    # === Master processing ===
    # Fade in/out
    if t < 1.0:
        sample *= t / 1.0
    if t > DURATION - 1.5:
        sample *= (DURATION - t) / 1.5

    # Soft clip / saturation
    if sample > 0:
        sample = 1.0 - math.exp(-sample * 2.5)
    else:
        sample = -(1.0 - math.exp(sample * 2.5))

    sample *= 0.85  # Master volume
    sample = max(-0.98, min(0.98, sample))
    samples.append(sample)

# Write WAV
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music.wav")
with wave.open(out_path, "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    for s in samples:
        wf.writeframes(struct.pack("<h", int(s * 32767)))

print(f"Generated {out_path} ({DURATION}s, {BPM}bpm, Am-F-C-G)")
