"""Pruebas unitarias sin llamadas a la API. Ejecutar: pytest -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.classifier_service import normalize, parse_json  # noqa: E402
from services.audio_service import AudioServiceError, transcribe  # noqa: E402
import pytest  # noqa: E402


def test_parse_json_con_bloque_de_codigo():
    raw = '```json\n{"categoria":"falla","prioridad":"alta"}\n```'
    assert parse_json(raw)["categoria"] == "falla"


def test_parse_json_invalido():
    assert parse_json("no es json") is None


def test_normalize_valores_invalidos():
    r = normalize({"categoria": "cualquier cosa", "prioridad": "urgente"}, "hola")
    assert r["categoria"] == "otros" and r["prioridad"] == "media"


def test_regla_critica_humo():
    r = normalize({"categoria": "mantenimiento", "prioridad": "baja"},
                  "Mi remalladora comenzó a botar humo y tiene olor a quemado.")
    assert r["prioridad"] == "critica" and r["categoria"] == "falla"
    assert r["requiere_atencion_tecnica"] is True


def test_audio_formato_no_soportado():
    with pytest.raises(AudioServiceError):
        transcribe(b"abc", "audio.ogg")
