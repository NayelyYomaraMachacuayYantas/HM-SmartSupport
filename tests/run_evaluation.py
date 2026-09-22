"""Ejecuta los 12 casos de prueba y genera evidence/matriz_pruebas.csv + métricas.

Uso:
  python tests/run_evaluation.py             # ejecuta casos y guarda CSV
  python tests/run_evaluation.py --metrics   # calcula métricas del CSV (tras llenar 'cumple' Sí/No)

Audios para casos 8-10: coloca en tests/audio/ -> caso08.wav, caso09.mp3 (o .m4a), caso10.wav
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.audio_service import AudioServiceError, transcribe  # noqa: E402
from services.chat_service import ChatServiceError, get_answer  # noqa: E402
from services.classifier_service import classify  # noqa: E402

CSV_PATH = ROOT / "evidence" / "matriz_pruebas.csv"
AUDIO_DIR = ROOT / "tests" / "audio"
FIELDS = ["ID", "Escenario", "Entrada", "Esperado", "Obtenido", "Tiempo_s",
          "Categoria_esp", "Prioridad_esp", "Categoria_obt", "Prioridad_obt",
          "Clasif_correcta", "Cumple", "Observaciones"]

# (id, escenario, turnos de entrada, esperado, categoria_esp, prioridad_esp)
CASES = [
    ("CP01", "Consulta simple", ["¿Qué es una remalladora y para qué sirve?"], "Respuesta pertinente al dominio", "informacion", "baja"),
    ("CP02", "Consulta de mantenimiento", ["¿Qué mantenimiento necesita una remalladora?"], "Orientación clara", "mantenimiento", "media"),
    ("CP03", "Consulta de configuración", ["¿Cómo enhebro una máquina de coser recta?"], "Pasos comprensibles", "configuracion", "media"),
    ("CP04", "Pregunta ambigua", ["No funciona"], "Solicita aclaración", "falla", "alta"),
    ("CP05", "Información desconocida", ["¿Cuál es el precio y stock exacto del modelo XZ-9000 Turbo?"], "No inventa información", "informacion", "baja"),
    ("CP06", "Tema fuera del dominio", ["¿Me das una receta de ceviche?"], "Redirige correctamente", "otros", "baja"),
    ("CP07", "Conversación con seguimiento",
     ["¿Qué mantenimiento necesita una remalladora?", "¿Y cada cuánto tiempo debo hacerlo?"], "Mantiene contexto", "mantenimiento", "media"),
    ("CP08", "Audio WAV", ["AUDIO:caso08"], "Transcribe correctamente", None, None),
    ("CP09", "Audio MP3/M4A", ["AUDIO:caso09"], "Transcribe correctamente", None, None),
    ("CP10", "Audio -> chatbot", ["AUDIO:caso10"], "Transcribe y responde", "falla", "critica"),
    ("CP11", "Falla técnica", ["Mi máquina recta hace un ruido fuerte y la aguja se rompe seguido."], "Clasifica categoría/prioridad", "falla", "alta"),
    ("CP12", "Situación crítica", ["Mi remalladora comenzó a botar humo y tiene olor a quemado."], "Asigna prioridad adecuada", "falla", "critica"),
]


def find_audio(stem: str):
    for ext in ("wav", "mp3", "m4a"):
        p = AUDIO_DIR / f"{stem}.{ext}"
        if p.exists():
            return p
    return None


def run_case(case) -> dict:
    cid, escenario, turnos, esperado, cat_e, pri_e = case
    row = {k: "" for k in FIELDS}
    row.update(ID=cid, Escenario=escenario, Esperado=esperado,
               Categoria_esp=cat_e or "", Prioridad_esp=pri_e or "")
    history, total_time, obtained, entrada, cls = [], 0.0, "", [], None
    try:
        for turn in turnos:
            if turn.startswith("AUDIO:"):
                path = find_audio(turn.split(":")[1])
                if not path:
                    row.update(Entrada=turn, Obtenido="PENDIENTE: falta archivo en tests/audio/")
                    return row
                turn_text = transcribe(path.read_bytes(), path.name)
                entrada.append(f"[{path.name}] -> {turn_text}")
                if cid != "CP10":     # CP08/CP09 solo evalúan transcripción
                    obtained = f"Transcripción: {turn_text}"
                    break
            else:
                turn_text = turn
                entrada.append(turn)
            history.append({"role": "user", "content": turn_text})
            answer, secs = get_answer(history, "V3")
            history.append({"role": "assistant", "content": answer})
            total_time += secs
            obtained = answer
            prev = [m["content"] for m in history if m["role"] == "user"][:-1][-2:]
            cls = classify(turn_text, contexto=" | ".join(prev) or None)
    except (ChatServiceError, AudioServiceError) as e:
        obtained = f"ERROR: {e}"

    row.update(Entrada=" || ".join(entrada), Obtenido=obtained.replace("\n", " ")[:600],
               Tiempo_s=f"{total_time:.2f}" if total_time else "")
    if cls:
        row.update(Categoria_obt=cls["categoria"], Prioridad_obt=cls["prioridad"])
        checks = []
        if cat_e:
            checks.append(cls["categoria"] == cat_e)
        if pri_e:
            checks.append(cls["prioridad"] == pri_e)
        if checks:
            row["Clasif_correcta"] = "Sí" if all(checks) else "No"
    return row


def compute_metrics() -> None:
    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    ejecutadas = [r for r in rows if r["Cumple"] in ("Sí", "No")]
    ok = [r for r in ejecutadas if r["Cumple"] == "Sí"]
    cl = [r for r in rows if r["Clasif_correcta"] in ("Sí", "No")]
    cl_ok = [r for r in cl if r["Clasif_correcta"] == "Sí"]
    tiempos = [float(r["Tiempo_s"]) for r in rows if r["Tiempo_s"]]
    print(f"Tasa de pruebas satisfactorias: {len(ok)}/{len(ejecutadas)} = {100*len(ok)/max(len(ejecutadas),1):.1f}%")
    print(f"Exactitud de clasificación:     {len(cl_ok)}/{len(cl)} = {100*len(cl_ok)/max(len(cl),1):.1f}%")
    print(f"Tiempo promedio de respuesta:   {sum(tiempos)/max(len(tiempos),1):.2f} s (n={len(tiempos)})")
    if len(tiempos) < 10:
        print("AVISO: la rúbrica pide al menos 10 consultas para el tiempo promedio. Repite pruebas o usa la app (promedio en la barra lateral).")


def main() -> None:
    if "--metrics" in sys.argv:
        compute_metrics()
        return
    CSV_PATH.parent.mkdir(exist_ok=True)
    rows = []
    for case in CASES:
        print(f"Ejecutando {case[0]} - {case[1]} ...")
        rows.append(run_case(case))
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nListo: {CSV_PATH}\nRevisa 'Obtenido', completa 'Cumple' (Sí/No) y 'Observaciones', luego ejecuta:\n  python tests/run_evaluation.py --metrics")


if __name__ == "__main__":
    main()
