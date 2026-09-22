"""Lógica del chatbot: cliente OpenRouter (API compatible con OpenAI)."""
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

from prompts.system_prompt import get_system_prompt
from services.config import get_settings

MAX_HISTORY_MESSAGES = 20  # límite de mensajes enviados como contexto


class ChatServiceError(Exception):
    """Error comprensible para mostrar al usuario."""


def make_client() -> OpenAI:
    s = get_settings()
    if not s.api_key or s.api_key == "tu_api_key_aqui":
        raise ChatServiceError(
            "No se encontró OPENROUTER_API_KEY. Crea un archivo .env a partir de "
            ".env.example y coloca tu clave de OpenRouter."
        )
    return OpenAI(
        base_url=s.base_url,
        api_key=s.api_key,
        timeout=60,
        max_retries=4,  # reintenta con espera creciente ante 429/5xx (por defecto: 2)
        default_headers={"HTTP-Referer": s.site_url, "X-Title": "HM Smart Support"},
    )


def complete(messages: list[dict], model: str | None = None,
             temperature: float = 0.3, max_tokens: int = 700) -> tuple[str, float]:
    """Llama al modelo y devuelve (texto, segundos). Traduce errores a mensajes claros."""
    client = make_client()
    model = model or get_settings().model
    start = time.perf_counter()
    try:
        resp = client.chat.completions.create(
            model=model, messages=messages,
            temperature=temperature, max_tokens=max_tokens,
        )
    except AuthenticationError:
        raise ChatServiceError("API Key inválida o sin permisos. Revisa tu archivo .env.")
    except RateLimitError:
        raise ChatServiceError("Límite de uso alcanzado (o modelo gratuito saturado). Espera un momento o cambia de modelo.")
    except APIConnectionError:
        raise ChatServiceError("No hay conexión con el servicio. Revisa tu internet e inténtalo nuevamente.")
    except APIStatusError as e:
        if e.status_code == 402:
            raise ChatServiceError("Créditos insuficientes en OpenRouter.")
        if e.status_code == 404:
            raise ChatServiceError(f"El modelo '{model}' no está disponible. Prueba con otro modelo.")
        raise ChatServiceError(f"El servicio respondió con error {e.status_code}. Inténtalo más tarde.")
    except OpenAIError as e:
        raise ChatServiceError(f"Error inesperado del servicio: {e}")
    elapsed = time.perf_counter() - start

    content = resp.choices[0].message.content if getattr(resp, "choices", None) else None
    if not content or not content.strip():
        raise ChatServiceError("El modelo devolvió una respuesta vacía. Inténtalo nuevamente.")
    return content.strip(), elapsed


def get_answer(history: list[dict], version: str = "V3", model: str | None = None) -> tuple[str, float]:
    """history: lista de {'role','content'} con el contexto de la conversación."""
    clean = [{"role": m["role"], "content": m["content"]} for m in history][-MAX_HISTORY_MESSAGES:]
    messages = [{"role": "system", "content": get_system_prompt(version)}] + clean
    return complete(messages, model=model, temperature=0.3, max_tokens=700)
