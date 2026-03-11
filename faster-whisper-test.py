"""
Faster Whisper - Teste de transcrição com CUDA (RTX 5060)
Uso: python faster-whisper-test.py [arquivo_audio]
Se nenhum arquivo for passado, grava 5 segundos do microfone.
"""
import sys
import os

def transcribe_file(audio_path, model_size="large-v3"):
    from faster_whisper import WhisperModel

    print(f"Carregando modelo '{model_size}' na GPU...")
    model = WhisperModel(model_size, device="cuda", compute_type="float16")
    print("Modelo carregado!")

    print(f"Transcrevendo: {audio_path}")
    segments, info = model.transcribe(audio_path, beam_size=5)

    print(f"Idioma detectado: {info.language} (probabilidade: {info.language_probability:.2f})")
    print(f"Duração: {info.duration:.1f}s")
    print("\n--- Transcrição ---")
    for segment in segments:
        print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}")
    print("--- Fim ---")

def record_and_transcribe():
    try:
        import sounddevice as sd
        import soundfile as sf
    except ImportError:
        print("Instalando sounddevice e soundfile para gravação...")
        os.system("pip install sounddevice soundfile")
        import sounddevice as sd
        import soundfile as sf

    duration = 5
    sample_rate = 16000
    temp_file = os.path.join(os.environ.get("TEMP", "/tmp"), "whisper_recording.wav")

    print(f"Gravando {duration} segundos... Fale agora!")
    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    print("Gravação concluída!")

    sf.write(temp_file, audio, sample_rate)
    transcribe_file(temp_file, model_size="large-v3")
    os.remove(temp_file)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if not os.path.exists(audio_file):
            print(f"Arquivo não encontrado: {audio_file}")
            sys.exit(1)
        transcribe_file(audio_file)
    else:
        print("Faster Whisper - Teste CUDA")
        print("=" * 40)
        print("Uso: python faster-whisper-test.py [arquivo.wav/mp3/etc]")
        print("Sem arquivo = grava do microfone por 5s")
        print()
        record_and_transcribe()
