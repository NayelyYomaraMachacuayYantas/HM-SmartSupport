"""Ejecuta las MISMAS consultas con V1, V2 y V3 y guarda evidence/comparacion_prompts.md
Uso: python tests/compare_prompts.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.chat_service import ChatServiceError, get_answer  # noqa: E402

QUERIES = [
    "¿Qué mantenimiento necesita una remalladora?",
    "Mi máquina hace ruido, ¿qué tiene?",
    "¿Cuál es el precio del modelo XZ-9000 Turbo?",
    "¿Me das una receta de ceviche?",
]


def main() -> None:
    out = ["# Comparación de prompts V1 vs V2 vs V3\n"]
    for q in QUERIES:
        out.append(f"\n## Consulta: {q}\n")
        for v in ("V1", "V2", "V3"):
            try:
                ans, secs = get_answer([{"role": "user", "content": q}], v)
            except ChatServiceError as e:
                ans, secs = f"ERROR: {e}", 0.0
            out.append(f"### {v} ({secs:.2f} s)\n\n{ans}\n")
            print(f"{v} | {q[:40]}... OK")
    path = ROOT / "evidence" / "comparacion_prompts.md"
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"\nGuardado en {path}")


if __name__ == "__main__":
    main()
