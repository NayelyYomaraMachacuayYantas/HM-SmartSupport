"""HM Smart Support - Asistente inteligente multimodal de postventa (Streamlit)."""
import importlib
import json

try:
    # Import dinamicamente para evitar errores estáticos del linter/IDE
    st = importlib.import_module("streamlit")
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "Falta la dependencia 'streamlit'. Instálala con: pip install streamlit"
    ) from exc

from prompts.system_prompt import VERSIONS
from services.audio_service import AudioServiceError, transcribe
from services.chat_service import ChatServiceError, get_answer
from services.classifier_service import classify
from services.config import get_settings

st.set_page_config(page_title="HM Smart Support", page_icon="🧵", layout="wide")

PRIORIDAD_ICONO = {"baja": "🟢", "media": "🟡", "alta": "🟠", "critica": "🔴"}


# ------------------------------------------------------------ estado de sesión
def init_state() -> None:
    st.session_state.setdefault("messages", [])          # historial (contexto)
    st.session_state.setdefault("transcription_text", "")
    st.session_state.setdefault("audio_name", "")


def reset_session() -> None:
    st.session_state["messages"] = []
    st.session_state["transcription_text"] = ""
    st.session_state["audio_name"] = ""
    st.session_state.pop("pending_query", None)


# --------------------------------------------------------------- componentes UI
def show_classification(cls: dict | None) -> None:
    if not cls:
        return
    icono = PRIORIDAD_ICONO.get(cls["prioridad"], "⚪")
    c1, c2, c3 = st.columns(3)
    c1.metric("Categoría", cls["categoria"].replace("_", " ").capitalize())
    c2.metric("Prioridad", f"{icono} {cls['prioridad'].capitalize()}")
    c3.metric("Atención técnica", "Sí" if cls["requiere_atencion_tecnica"] else "No")
    if cls.get("recomendacion"):
        st.caption(f"💡 {cls['recomendacion']}")
    with st.expander("Ver salida estructurada (JSON)"):
        st.code(json.dumps(cls, ensure_ascii=False, indent=2), language="json")


def render_history() -> None:
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            if m.get("source") == "audio":
                st.caption("🎙️ Consulta proveniente de audio")
            st.markdown(m["content"])
            if m["role"] == "assistant":
                show_classification(m.get("classification"))
                if m.get("seconds") is not None:
                    st.caption(f"⏱ {m['seconds']:.2f} s")


def handle_query(query: str, source: str, version: str, model: str) -> None:
    with st.chat_message("user"):
        if source == "audio":
            st.caption("🎙️ Consulta proveniente de audio")
        st.markdown(query)
    previous_users = [m["content"] for m in st.session_state["messages"] if m["role"] == "user"][-2:]
    st.session_state["messages"].append({"role": "user", "content": query, "source": source})

    with st.chat_message("assistant"):
        try:
            with st.spinner("Analizando tu consulta..."):
                answer, secs = get_answer(st.session_state["messages"], version, model)
        except ChatServiceError as e:
            st.error(f"⚠️ {e}")
            st.session_state["messages"].pop()  # no contaminar el contexto
            return
        st.markdown(answer)

        cls = None
        try:
            cls = classify(query, model, contexto=" | ".join(previous_users) or None)
            show_classification(cls)
        except ChatServiceError as e:
            st.warning(f"No se pudo clasificar la consulta: {e}")
        st.caption(f"⏱ {secs:.2f} s")

    st.session_state["messages"].append(
        {"role": "assistant", "content": answer, "classification": cls, "seconds": secs}
    )


# ------------------------------------------------------------------ programa
init_state()
settings = get_settings()

with st.sidebar:
    st.header("⚙️ Configuración")
    version = st.selectbox("Versión del prompt", list(VERSIONS), index=2,
                           format_func=lambda k: VERSIONS[k])
    model = st.text_input("Modelo (OpenRouter)", value=settings.model)
    if st.button("🔄 Reiniciar sesión", use_container_width=True):
        reset_session()
        st.rerun()

    st.divider()
    st.subheader("🎙️ Consulta por audio")
    audio = st.file_uploader("Sube un audio (MP3, WAV o M4A)", type=["mp3", "wav", "m4a"])
    if audio is not None:
        st.caption(f"📁 Archivo: **{audio.name}**")
        st.audio(audio)
        if st.button("📝 Transcribir audio", use_container_width=True):
            try:
                with st.spinner("Transcribiendo (la primera vez descarga el modelo)..."):
                    st.session_state["transcription_text"] = transcribe(audio.getvalue(), audio.name)
                    st.session_state["audio_name"] = audio.name
            except AudioServiceError as e:
                st.error(f"⚠️ {e}")

    st.text_area("Transcripción (editable)", key="transcription_text", height=140)
    if st.button("➡️ Usar como consulta", use_container_width=True):
        if st.session_state["transcription_text"].strip():
            st.session_state["pending_query"] = (st.session_state["transcription_text"].strip(), "audio")
        else:
            st.warning("Primero transcribe un audio.")

    st.divider()
    times = [m["seconds"] for m in st.session_state["messages"] if m.get("seconds") is not None]
    if times:
        st.metric("Tiempo promedio de respuesta", f"{sum(times) / len(times):.2f} s")

st.title("🧵 HM Smart Support")
st.caption("Asistente inteligente multimodal de postventa — Hilos y Máquinas S.A.C.")

render_history()

typed = st.chat_input("Escribe tu consulta sobre tu máquina...")
pending = st.session_state.pop("pending_query", None)
if typed:
    handle_query(typed, "texto", version, model)
elif pending:
    handle_query(pending[0], pending[1], version, model)
