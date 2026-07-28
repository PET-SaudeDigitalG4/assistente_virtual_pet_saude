import logging
from typing import TYPE_CHECKING, Optional

from api.models.models import User, Chat, Message
from api.schemas.responses import ChatResponse
from api.utils.logger import DbLogger
from api.services.config_service import ConfigService

from api.services.menu_handlers import handle_dynamic_menu, TEXTS

if TYPE_CHECKING:  # pragma: no cover
    # Import so em tempo de tipagem: NLPService arrasta LangChain e o modelo de
    # embeddings, o que tiraria a maquina de estados do alcance dos testes.
    from api.services.nlp_service import NLPService

logger = logging.getLogger("AppLogger")

COMANDOS_MENU = ("menu", "/menu")
COMANDO_RESETAR = "/resetar"

APRESENTACAO = "Olá! Sou o assistente virtual da Secretaria Municipal de Saúde."


def normalizar_id_wpp(id_wpp: str) -> str:
    """Reduz o identificador ao numero, seja qual for o gateway.

    A Twilio entrega "whatsapp:+5577999999999" e a Evolution API entrega
    "5577999999999". Sem normalizar, o mesmo cidadao vira dois usuarios com
    estados independentes.
    """
    return "".join(c for c in (id_wpp or "") if c.isdigit())


class ChatService:
    def __init__(self, db, nlp_service: "NLPService"):
        self.db = db
        self.nlp = nlp_service
        self.config_service = ConfigService(db)

    async def process_message(self, id_wpp: str, text: str) -> ChatResponse:
        # Guardado a parte: depois de um rollback, tocar no objeto User pode
        # disparar refresh e estourar de novo dentro do proprio except.
        user_id = None
        try:
            text = (text or "").strip()

            if not text:
                return ChatResponse(text="Não entendi sua mensagem. Pode repetir?")

            clean_text = self._clean_text(text)

            user = self._get_or_create_user(id_wpp)
            user_id = user.id
            chat = self._get_or_create_chat(user)

            DbLogger.log_event(
                self.db,
                "INFO",
                "MESSAGE_RECEIVED",
                f"Mensagem recebida de {user.id_wpp}",
                user_id=user.id
            )

            self._save_message(chat, text, "user")

            response = self._responder(user, clean_text)
            response = self._ensure_chat_response(response)

            self._save_message(chat, response.text, "bot")
            self.db.commit()

            return response

        except Exception as e:
            self.db.rollback()
            logger.exception("Falha ao processar mensagem de %s", id_wpp)
            DbLogger.log_event(
                self.db,
                "ERROR",
                "MESSAGE_FAILED",
                f"Falha ao processar mensagem: {e}",
                user_id=user_id,
                meta={"id_wpp": id_wpp, "erro": type(e).__name__},
            )
            return ChatResponse(text="Desculpe, ocorreu um erro interno.")

    def _responder(self, user: User, clean_text: str) -> ChatResponse:
        if clean_text.lower() == COMANDO_RESETAR:
            return self._resetar(user)

        if not user.state:
            user.state = "NEW"
        elif user.state not in ("NEW", "WAITING_NAME") and user.state not in TEXTS:
            user.state = "WAITING_MAIN_MENU"

        if clean_text.lower() in COMANDOS_MENU:
            return self._voltar_ao_menu(user)

        if user.state == "NEW":
            return self._primeiro_contato(user, clean_text)

        if user.state == "WAITING_NAME":
            return self._registrar_nome(user, clean_text)

        return self._dentro_do_menu(user, clean_text)

    def _resetar(self, user: User) -> ChatResponse:
        # Limpar o nome junto: mantendo-o, o ramo NEW pula o onboarding e o
        # usuario nunca consegue corrigir um nome digitado errado.
        user.state = "NEW"
        user.name = None
        return ChatResponse(
            text="Conversa reiniciada!\nEnvie uma mensagem para começar."
        )

    def _voltar_ao_menu(self, user: User) -> ChatResponse:
        if not user.name:
            user.state = "WAITING_NAME"
            return ChatResponse(
                text=f"{APRESENTACAO}\nPara acessar o menu, digite apenas o seu nome:"
            )

        user.state = "WAITING_MAIN_MENU"
        return ChatResponse(
            text=f"Voltando ao menu principal...\n\n{TEXTS['WAITING_MAIN_MENU']['text']}"
        )

    def _primeiro_contato(self, user: User, clean_text: str) -> ChatResponse:
        if not user.name:
            user.state = "WAITING_NAME"
            return ChatResponse(
                text=f"{APRESENTACAO}\nPara continuar, digite apenas o seu nome:"
            )

        user.state = "WAITING_MAIN_MENU"
        rag_response = self._perguntar_ao_rag(clean_text, user.name) or f"Oi, {user.name}!"
        return ChatResponse(
            text=f"{rag_response}\n\n{TEXTS['WAITING_MAIN_MENU']['text']}"
        )

    def _registrar_nome(self, user: User, clean_text: str) -> ChatResponse:
        nome = self._extract_name(clean_text)

        if len(nome) < 2:
            return ChatResponse(text="Digite um nome válido.")
        if len(nome) > 30:
            return ChatResponse(text="Nome muito longo. Digite apenas seu primeiro nome.")
        if any(char.isdigit() for char in nome):
            return ChatResponse(text="O nome não deve conter números.")
        if len(nome.split()) > 3:
            return ChatResponse(text="Digite apenas seu primeiro nome.")

        user.name = nome
        user.state = "WAITING_MAIN_MENU"
        return ChatResponse(
            text=(
                f"Prazer, {user.name}! 😊\n"
                "Como posso te ajudar hoje?\n\n"
                f"{TEXTS['WAITING_MAIN_MENU']['text']}"
            )
        )

    def _dentro_do_menu(self, user: User, clean_text: str) -> ChatResponse:
        state_config = TEXTS[user.state]
        current_menu_text = state_config["text"]

        if state_config.get("options", {}).get(clean_text):
            return handle_dynamic_menu(user, clean_text, self.nlp, self.db)

        if clean_text.isdigit():
            return self._opcao_invalida(current_menu_text)

        if self._em_manutencao():
            return ChatResponse(text="O Chat Bot está em manutenção.")

        rag_response = self._perguntar_ao_rag(clean_text, user.name)

        if not rag_response:
            return self._opcao_invalida(current_menu_text)

        return ChatResponse(text=f"{rag_response}\n\n{current_menu_text}")

    def _opcao_invalida(self, menu_text: str) -> ChatResponse:
        return ChatResponse(
            text=f"Opção inválida. Por favor, digite um número válido:\n\n{menu_text}"
        )

    def _em_manutencao(self) -> bool:
        return self.config_service.get_config("maintenance_mode", "false") == "true"

    def _perguntar_ao_rag(self, texto: str, user_name: Optional[str]) -> Optional[str]:
        """None quando o RAG nao achou resposta ou quando ele explodiu.

        NLPService.process ja devolve None para 'nao encontrei no contexto', o
        que dispensa procurar palavras de erro dentro da resposta.
        """
        try:
            return self.nlp.process(texto, user_name=user_name)
        except Exception:
            logger.exception("NLPService falhou para: %r", texto)
            return None

    def _ensure_chat_response(self, response) -> ChatResponse:
        if isinstance(response, ChatResponse):
            return response
        return ChatResponse(text=str(response))

    def _clean_text(self, text: str) -> str:
        # Antes isto cortava tudo antes do ultimo ":", para remover prefixo de
        # gateway. Efeito colateral: "Horário: 8 às 17" virava "8 às 17".
        # Prefixo de gateway, se voltar, e problema da rota, nao do dominio.
        return " ".join((text or "").strip().split())

    def _extract_name(self, text: str) -> str:
        return self._clean_text(text)

    def _get_or_create_user(self, id_wpp: str) -> User:
        id_wpp = normalizar_id_wpp(id_wpp) or id_wpp
        user = self.db.query(User).filter(User.id_wpp == id_wpp).first()
        if not user:
            user = User(id_wpp=id_wpp, state="NEW")
            self.db.add(user)
            self.db.flush()
        return user

    def _get_or_create_chat(self, user: User) -> Chat:
        chat = self.db.query(Chat).filter(Chat.user_id == user.id).first()
        if not chat:
            chat = Chat(user=user)
            self.db.add(chat)
            self.db.flush()
        return chat

    def _save_message(self, chat: Chat, text: str, sender: str) -> Message:
        message = Message(chat=chat, text=str(text), sender=sender)
        self.db.add(message)
        self.db.flush()
        return message
