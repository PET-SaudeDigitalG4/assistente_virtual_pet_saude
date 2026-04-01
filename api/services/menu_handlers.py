import json
import os
from typing import Optional

from api.schemas.responses import ChatResponse
from api.services.config_service import ConfigService
from api.services.flow_media_service import FlowMediaService

diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_json = os.path.join(diretorio_atual, "menu_texts.json")

with open(caminho_json, "r", encoding="utf-8") as file:
    TEXTS = json.load(file)


def build_response(text: str, image_key: Optional[str] = None, db=None) -> ChatResponse:
    image_url = None

    if image_key:
        image_url = _resolve_image_url(image_key, db=db)

    return ChatResponse(text=text, image_url=image_url)


def _resolve_image_url(image_key: str, db=None) -> Optional[str]:
    if db is not None:
        flow_media_value = FlowMediaService(db).get_active_image_url(image_key)
        if flow_media_value:
            return flow_media_value

        config_value = ConfigService(db).get_flow_image_url(image_key)
        if config_value:
            return config_value

    env_value = os.getenv(f"FLOW_IMAGE_{image_key.upper()}")
    if env_value:
        return env_value

    return TEXTS.get("FLOW_IMAGE_URLS", {}).get(image_key) or None


def handle_voltar_menu_principal(user, db) -> ChatResponse:
    user.state = "WAITING_MAIN_MENU_CHOICE"
    return build_response(TEXTS["MAIN_MENU_TEXT"], db=db)


def handle_abrir_triagem(user, db) -> ChatResponse:
    user.state = "TRIAGEM_FLOW"
    return build_response(
        "Você escolheu 📋 *Triagem para Agendamento*.\nPor favor, digite qual especialidade você busca (ex: tomografia):\n\n"
        "*Digite 0 a qualquer momento para voltar ao menu principal*",
        db=db,
    )


def handle_abrir_farmacia(user, db) -> ChatResponse:
    user.state = "WAITING_FARMACIA_CHOICE"
    return build_response(TEXTS["FARMACIA_MENU_TEXT"], db=db)


def handle_abrir_vacinacao(user, db) -> ChatResponse:
    user.state = "WAITING_VACINACAO_CHOICE"
    return build_response(TEXTS["VACINACAO_MENU_TEXT"], db=db)


def handle_abrir_servicos_rede(user, db) -> ChatResponse:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"
    return build_response(TEXTS["SERVICOS_REDE_MENU_TEXT"], db=db)


def handle_farm_sus(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS["QUERIES_RAG"]["REMEDIOS"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "REMEDIOS",
        db=db,
    )


def handle_farm_rede(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS["QUERIES_RAG"]["FARM_POPULAR"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "FARM_POPULAR",
        db=db,
    )


def handle_farm_orientacoes(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS["QUERIES_RAG"]["ORIENTACOES"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "ORIENTACOES",
        db=db,
    )


def handle_vac_calendario(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS["QUERIES_RAG"]["CALENDARIO"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "CALENDARIO",
        db=db,
    )


def handle_vac_insumos(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS["QUERIES_RAG"]["INSUMOS"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "INSUMOS",
        db=db,
    )


def handle_vac_sesab(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS["QUERIES_RAG"]["PROTOCOLO"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "PROTOCOLO",
        db=db,
    )


def handle_vac_componentes(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS["QUERIES_RAG"]["COMP_ESPECIALIZADOS"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "COMP_ESPECIALIZADOS",
        db=db,
    )


def handle_servicos_cemae(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"

    query = TEXTS["QUERIES_RAG"]["CEMAE"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "CEMAE",
        db=db,
    )


def handle_servicos_cemerf(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"

    query = TEXTS["QUERIES_RAG"]["CEMERF"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "CEMERF",
        db=db,
    )


def handle_servicos_acesso(user, db, nlp_service) -> ChatResponse:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"

    query = TEXTS["QUERIES_RAG"]["ACESSO_SERVICOS"]
    rag_answer = nlp_service.process(query)

    return build_response(
        f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*",
        "ACESSO_SERVICOS",
        db=db,
    )


MAIN_MENU_OPTIONS = {
    "1": handle_abrir_triagem,
    "2": handle_abrir_farmacia,
    "3": handle_abrir_vacinacao,
    "4": handle_abrir_servicos_rede,
}

FARMACIA_MENU_OPTIONS = {
    "1": handle_farm_sus,
    "2": handle_farm_rede,
    "3": handle_farm_orientacoes,
    "0": handle_voltar_menu_principal,
}

VACINACAO_MENU_OPTIONS = {
    "1": handle_vac_calendario,
    "2": handle_vac_insumos,
    "3": handle_vac_sesab,
    "4": handle_vac_componentes,
    "0": handle_voltar_menu_principal,
}

SERVICOS_REDE_MENU_OPTIONS = {
    "1": handle_servicos_cemae,
    "2": handle_servicos_cemerf,
    "3": handle_servicos_acesso,
    "0": handle_voltar_menu_principal,
}

MENU_ROUTER = {
    "WAITING_MAIN_MENU_CHOICE": (MAIN_MENU_OPTIONS, TEXTS["MAIN_MENU_TEXT"]),
    "WAITING_FARMACIA_CHOICE": (FARMACIA_MENU_OPTIONS, TEXTS["FARMACIA_MENU_TEXT"]),
    "WAITING_VACINACAO_CHOICE": (VACINACAO_MENU_OPTIONS, TEXTS["VACINACAO_MENU_TEXT"]),
    "WAITING_SERVICOS_REDE_CHOICE": (SERVICOS_REDE_MENU_OPTIONS, TEXTS["SERVICOS_REDE_MENU_TEXT"]),
}
