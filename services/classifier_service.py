"""Clasificación de consultas: categoría, prioridad y salida JSON estructurada."""
import json
import re
import unicodedata

from prompts.system_prompt import CLASSIFIER_PROMPT
from services.chat_service import complete

CATEGORIAS = ["informacion", "configuracion", "mantenimiento", "garantia",
              "repuesto", "falla", "servicio_tecnico", "otros"]
PRIORIDADES = ["baja", "media", "alta", "critica"]

# Regla de seguridad determinista: garantiza consistencia en situaciones críticas.
PALABRAS_CRITICAS = ["humo", "quemado", "quemando", "chispa", "cortocircuito",
                     "descarga electrica", "me dio corriente", "incendio", "fuego",
                     "sobrecalent", "se calienta demasiado"]


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).lower().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def parse_json(text: str) -> dict | None:
    """Extrae el primer objeto JSON del texto (tolera ```json ... ```)."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        data = json.loads(text[start:end + 1])
        return data if isinstance(data, dict) else None
    except json.JSONDecodeError:
        return None


def _to_bool(v) -> bool:
    if isinstance(v, bool):
        return v
    return _norm(v) in {"true", "si", "yes", "1"}


def normalize(data: dict | None, consulta: str) -> dict:
    """Valida valores permitidos y aplica regla de seguridad."""
    data = data or {}
    cat = _norm(data.get("categoria", "otros")).replace(" ", "_")
    pri = _norm(data.get("prioridad", "media"))
    result = {
        "categoria": cat if cat in CATEGORIAS else "otros",
        "prioridad": pri if pri in PRIORIDADES else "media",
        "equipo": str(data.get("equipo", "no especificado")),
        "problema": str(data.get("problema", "ninguno")),
        "requiere_atencion_tecnica": _to_bool(data.get("requiere_atencion_tecnica", False)),
        "recomendacion": str(data.get("recomendacion", "")),
    }
    if any(k in _norm(consulta) for k in PALABRAS_CRITICAS):
        result["categoria"] = "falla"
        result["prioridad"] = "critica"
        result["requiere_atencion_tecnica"] = True
        if "detener" not in _norm(result["recomendacion"]):
            result["recomendacion"] = "Detener el uso del equipo, desconectarlo y solicitar evaluación técnica."
    if not data:
        result["recomendacion"] = result["recomendacion"] or "No se pudo clasificar automáticamente; derivar a un agente."
    return result


def classify(consulta: str, model: str | None = None, contexto: str | None = None) -> dict:
    """Devuelve el diccionario de clasificación. Puede lanzar ChatServiceError."""
    texto = consulta if not contexto else f"(Contexto previo del cliente: {contexto})\n{consulta}"
    messages = [
        {"role": "system", "content": CLASSIFIER_PROMPT},
        {"role": "user", "content": f"<consulta>{texto}</consulta>"},
    ]
    raw, _ = complete(messages, model=model, temperature=0.0, max_tokens=300)
    return normalize(parse_json(raw), consulta)
