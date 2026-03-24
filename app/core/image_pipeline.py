import base64
import mimetypes
import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()

DEFAULT_IMAGE_PROMPT = (
    "Analise a imagem enviada e responda em portugues de forma clara e objetiva. "
    "Se houver texto visivel, considere-o na resposta."
)
VISION_MODEL_NAME = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")


def _guess_mime_type(image_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(image_path)
    return mime_type or "image/jpeg"


def _encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def _get_vision_llm() -> ChatGroq:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("A chave da API Groq nao foi encontrada.")

    return ChatGroq(
        model=VISION_MODEL_NAME,
        temperature=0.2,
        max_tokens=700,
        api_key=api_key,
    )


def analyze_image(image_path: str, prompt: str | None = None) -> str:
    if not image_path:
        return "Envie uma imagem valida para analise."

    if not os.path.exists(image_path):
        return "Nao foi possivel localizar a imagem enviada."

    llm = _get_vision_llm()
    mime_type = _guess_mime_type(image_path)
    image_base64 = _encode_image(image_path)
    user_prompt = (prompt or "").strip() or DEFAULT_IMAGE_PROMPT

    message = HumanMessage(
        content=[
            {"type": "text", "text": user_prompt},
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{image_base64}"
                },
            },
        ]
    )

    response = llm.invoke([message])
    return str(response.content).strip()
