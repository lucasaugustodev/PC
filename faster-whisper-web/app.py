import os
import sys
import asyncio
import base64

# Add NVIDIA DLL paths before importing anything CUDA-related
nvidia_path = os.path.join(sys.prefix, "Lib", "site-packages", "nvidia")
for lib in ["cublas", "cudnn"]:
    bin_path = os.path.join(nvidia_path, lib, "bin")
    if os.path.isdir(bin_path):
        os.environ["PATH"] = bin_path + os.pathsep + os.environ.get("PATH", "")

from flask import Flask, request, jsonify, send_file, send_from_directory, Response
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

@app.route("/avatars/<path:filename>")
def serve_avatar(filename):
    return send_from_directory("avatars", filename)

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
        language = request.form.get("language", "pt")
        segments, info = model.transcribe(tmp.name, beam_size=5, language=language)
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
    with_lipsync = data.get("lipsync", False)

    if not text:
        return jsonify({"error": "Texto vazio"}), 400

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tmp.close()

    try:
        async def generate():
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp.name)
        asyncio.run(generate())
    except Exception as e:
        os.unlink(tmp.name)
        return jsonify({"error": str(e)}), 500

    if not with_lipsync:
        with open(tmp.name, "rb") as f:
            audio_data = f.read()
        os.unlink(tmp.name)
        return Response(audio_data, mimetype="audio/mpeg")

    # Lipsync mode: transcribe TTS audio to get word timestamps
    try:
        segments, info = model.transcribe(
            tmp.name, beam_size=5, word_timestamps=True
        )
        words = []
        wtimes = []
        wdurations = []
        for seg in segments:
            if seg.words:
                for w in seg.words:
                    words.append(w.word.strip())
                    wtimes.append(int(w.start * 1000))
                    wdurations.append(int((w.end - w.start) * 1000))

        with open(tmp.name, "rb") as f:
            audio_b64 = base64.b64encode(f.read()).decode("utf-8")

        return jsonify({
            "audio": audio_b64,
            "words": words,
            "wtimes": wtimes,
            "wdurations": wdurations
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.unlink(tmp.name)

@app.route("/upload-avatar", methods=["POST"])
def upload_avatar():
    if "avatar" not in request.files:
        return jsonify({"error": "Nenhum arquivo enviado"}), 400
    f = request.files["avatar"]
    filename = f.filename.replace(" ", "_")
    path = os.path.join("avatars", filename)
    f.save(path)
    return jsonify({"url": "/avatars/" + filename})

@app.route("/voices")
def voices():
    async def get_voices():
        return await edge_tts.list_voices()
    all_voices = asyncio.run(get_voices())
    pt_voices = [v for v in all_voices if v["Locale"].startswith("pt-")]
    return jsonify(pt_voices)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=False)
