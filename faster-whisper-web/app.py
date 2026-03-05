import os
import sys
import asyncio

# Add NVIDIA DLL paths before importing anything CUDA-related
nvidia_path = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
for lib in ["cublas", "cudnn"]:
    bin_path = os.path.join(nvidia_path, lib, "bin")
    if os.path.isdir(bin_path):
        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")

from flask import Flask, request, jsonify, send_file, Response
from faster_whisper import WhisperModel
import edge_tts
import tempfile
import time

app = Flask(__name__)

print("Carregando modelo large-v3 na GPU... (pode demorar na primeira vez)")
model = WhisperModel("C:/Users/PC/.cache/faster-whisper-large-v3", device="cuda", compute_type="float16")
print("Modelo carregado e pronto!")

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "Nenhum audio enviado"}), 400

    audio_file = request.files["audio"]
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    audio_file.save(tmp.name)
    tmp.close()

    try:
        start = time.time()
        segments, info = model.transcribe(tmp.name, beam_size=5)
        results = []
        full_text = ""
        for seg in segments:
            results.append({
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text
            })
            full_text += seg.text

        elapsed = time.time() - start
        return jsonify({
            "text": full_text.strip(),
            "segments": results,
            "language": info.language,
            "language_probability": round(info.language_probability, 2),
            "duration": round(info.duration, 1),
            "processing_time": round(elapsed, 2)
        })
    finally:
        os.unlink(tmp.name)

@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json()
    text = data.get("text", "").strip()
    voice = data.get("voice", "pt-BR-AntonioNeural")

    if not text:
        return jsonify({"error": "Texto vazio"}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.close()

    async def generate():
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(tmp.name)

    try:
        asyncio.run(generate())
    except Exception as e:
        os.unlink(tmp.name)
        return jsonify({"error": str(e)}), 500

    def send_and_cleanup():
        with open(tmp.name, "rb") as f:
            data = f.read()
        os.unlink(tmp.name)
        return data

    audio_data = send_and_cleanup()
    return Response(audio_data, mimetype="audio/mpeg")

@app.route("/voices")
def voices():
    async def get_voices():
        return await edge_tts.list_voices()

    all_voices = asyncio.run(get_voices())
    pt_voices = [v for v in all_voices if v["Locale"].startswith("pt-")]
    return jsonify(pt_voices)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=False)
