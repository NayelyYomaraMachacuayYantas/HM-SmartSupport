"""Prueba que WAV, MP3 y M4A transcriben con Whisper.
Uso: python tests/probar_formatos.py > evidence/prueba_formatos_audio.txt
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.audio_service import AudioServiceError, transcribe  # noqa: E402
from services.config import get_settings  # noqa: E402

ARCHIVOS = ("caso08.wav", "caso09.mp3", "caso09.m4a", "caso10.wav")


def main() -> None:
    print(f"Modelo Whisper: {get_settings().whisper_size}\n")
    fallos = 0
    for name in ARCHIVOS:
        p = ROOT / "tests" / "audio" / name
        if not p.exists():
            print(f"[FALTA] {name}")
            fallos += 1
            continue
        try:
            print(f"[OK]    {name} -> {transcribe(p.read_bytes(), p.name)}")
        except AudioServiceError as e:
            print(f"[ERROR] {name} -> {e}")
            fallos += 1
    print(f"\nResultado: {len(ARCHIVOS) - fallos}/{len(ARCHIVOS)} formatos transcritos correctamente")


if __name__ == "__main__":
    main()
