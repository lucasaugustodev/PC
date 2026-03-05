from flask import Flask, request, jsonify, send_file
from faster_whisper import WhisperModel
import tempfile
import os
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555, debug=False)
