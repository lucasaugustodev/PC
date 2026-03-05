# Faster Whisper Web + Edge TTS

Interface web local para transcrição de voz (Speech-to-Text) e síntese de fala (Text-to-Speech).

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![CUDA](https://img.shields.io/badge/CUDA-GPU%20Accelerated-green)
![License](https://img.shields.io/badge/License-MIT-yellow)

## Funcionalidades

### Voz para Texto (STT)
- Transcrição em tempo real usando [Faster Whisper](https://github.com/SYSTRAN/faster-whisper) com modelo **large-v3**
- Aceleração por GPU via CUDA (float16)
- Detecção automática de idioma
- Segmentação temporal do áudio
- Gravação direta pelo navegador

### Texto para Voz (TTS)
- Síntese de fala usando [Edge TTS](https://github.com/rany2/edge-tts) (vozes Microsoft Neural)
- 5 vozes em Português disponíveis (BR e PT)
- Reprodução automática e histórico de áudios gerados
- Sem limite de caracteres

## Requisitos

- Python 3.11+
- GPU NVIDIA com suporte CUDA
- Driver NVIDIA com CUDA 12+

## Instalação

```bash
# Instalar dependências
pip install faster-whisper flask edge-tts

# Instalar bibliotecas CUDA (se necessário)
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

# Baixar o modelo (primeira execução faz automaticamente, ~3GB)
python -c "from huggingface_hub import snapshot_download; snapshot_download('Systran/faster-whisper-large-v3', local_dir='models/large-v3')"
```

## Uso

```bash
python app.py
```

Acesse http://localhost:5555 no navegador.

## Vozes TTS Disponíveis

| Voz | Idioma | Gênero |
|-----|--------|--------|
| Francisca | PT-BR | Feminino |
| Antonio | PT-BR | Masculino |
| Thalita | PT-BR | Feminino (Multilingual) |
| Raquel | PT-PT | Feminino |
| Duarte | PT-PT | Masculino |

## Stack

- **Backend:** Flask + Faster Whisper + Edge TTS
- **Frontend:** HTML/CSS/JS vanilla
- **GPU:** CTranslate2 com CUDA (float16)
- **Modelo:** Whisper large-v3 (Systran/faster-whisper-large-v3)
