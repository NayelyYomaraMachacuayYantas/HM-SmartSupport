"""Transcripción de audio (MP3, WAV, M4A) con Whisper local (faster-whisper)."""
import os
import tempfile
from functools import lru_cache

from services.config import get_settings

ALLOWED_EXTENSIONS = {"mp3", "wav", "m4a"}


class AudioServiceError(Exception):
    """Error comprensible de procesamiento de audio."""


@lru_cache(maxsize=1)
def _load_model(size: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise AudioServiceError("Falta la librería faster-whisper. Ejecuta: pip install -r requirements.txt")
    return WhisperModel(size, device="cpu", compute_type="int8")


def transcribe(file_bytes: bytes, filename: str, language: str = "es") -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise AudioServiceError(f"Formato .{ext or '?'} no soportado. Usa MP3, WAV o M4A.")
    if not file_bytes:
        raise AudioServiceError("El archivo de audio está vacío.")

    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
            tmp.write(file_bytes)
            path = tmp.name
        model = _load_model(get_settings().whisper_size)
        segments, _info = model.transcribe(path, language=language, vad_filter=True)
        text = " ".join(seg.text.strip() for seg in segments).strip()
    except AudioServiceError:
        raise
    except Exception as e:  # audio corrupto, códec no legible, etc.
        raise AudioServiceError(f"No se pudo transcribir el audio: {e}")
    finally:
        if path and os.path.exists(path):
            os.remove(path)

    if not text:
        raise AudioServiceError("No se detectó voz en el audio. Prueba con otra grabación.")
    return text
