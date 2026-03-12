"""Generate a simple loopable electronic beat as WAV."""
import struct, math, wave, os

SR = 44100
DURATION = 9  # seconds
BPM = 120
beat_len = int(SR * 60 / BPM)

samples = []

for i in range(SR * DURATION):
    t = i / SR
    beat_pos = i % beat_len
    bar_pos = i % (beat_len * 4)

    # Kick drum - every beat
    kick = 0.0
    if beat_pos < int(SR * 0.08):
        kick_t = beat_pos / SR
        kick_freq = 150 * math.exp(-kick_t * 40)
        kick = math.sin(2 * math.pi * kick_freq * kick_t) * math.exp(-kick_t * 25) * 0.5

    # Hi-hat - offbeat (8th notes)
    hihat = 0.0
    eighth = beat_len // 2
    hat_pos = i % eighth
    if hat_pos < int(SR * 0.02):
        hat_t = hat_pos / SR
        # Noise-like via high freq sines
        hihat = sum(math.sin(2 * math.pi * f * hat_t) for f in [6000, 8000, 10000, 12000]) / 4
        hihat *= math.exp(-hat_t * 150) * 0.12

    # Sub bass - root note pulsing
    bass_freq = 55  # A1
    bass_env = 0.3 + 0.1 * math.sin(2 * math.pi * t * (BPM / 60) / 4)
    bass = math.sin(2 * math.pi * bass_freq * t) * bass_env * 0.25

    # Pad / atmosphere - slow chord
    pad = 0.0
    pad_freqs = [220, 277.18, 329.63, 440]  # Am chord
    for j, freq in enumerate(pad_freqs):
        pad += math.sin(2 * math.pi * freq * t + math.sin(t * 0.5) * 0.3) * 0.04

    # Mix
    sample = kick + hihat + bass + pad

    # Fade in/out
    if t < 0.5:
        sample *= t / 0.5
    if t > DURATION - 0.5:
        sample *= (DURATION - t) / 0.5

    # Soft clip
    sample = max(-0.9, min(0.9, sample))
    samples.append(sample)

# Write WAV
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "beat.wav")
with wave.open(out_path, "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    for s in samples:
        wf.writeframes(struct.pack("<h", int(s * 32767)))

print(f"Generated {out_path} ({len(samples)} samples, {DURATION}s)")
