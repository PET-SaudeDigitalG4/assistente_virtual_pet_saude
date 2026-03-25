from api.models.models import User, Chat, Message
from api.services.nlp_service import NLPService
from api.utils.logger import DbLogger
from api.services.config_service import ConfigService
from api.services.menu_handlers import MENU_ROUTER, TEXTS

class ChatService:
    def __init__(self, db, nlp_service: NLPService):
        self.db = db
        self.nlp = nlp_service
        self.config_service = ConfigService(db)

    async def process_message(self, id_wpp: str, text: str) -> str:
        try:
            text = (text or "").strip()

            if not text:
                return "Não entendi sua mensagem. Pode repetir?"

            clean_text = self._clean_text(text)

            user = self._get_or_create_user(id_wpp)
            chat = self._get_or_create_chat(user)

            print("STATE ANTES:", user.state)

            DbLogger.log_event(
                self.db,
                "INFO",
                "MESSAGE_RECEIVED",
                f"Mensagem recebida de {id_wpp}",
                user_id=user.id
            )

            self._save_message(chat, text, "user")

            if clean_text.lower() == "/resetar":
                user.state = "NEW"
                self.db.commit()
                return "Conversa reiniciada!\nEnvie uma mensagem para começar."

            if not user.state:
                user.state = "NEW"

            comandos_menu = ["0", "menu", "/menu"]

            if clean_text.lower() in comandos_menu:
                user.state = "WAITING_MAIN_MENU_CHOICE"
                response_text = f"Voltando ao menu principal...\n\n{TEXTS['MAIN_MENU_TEXT']}"

            elif user.state == "NEW":
                if user.name:
                    user.state = "WAITING_MAIN_MENU_CHOICE"
                    rag_response = self.nlp.process(clean_text, user_name=user.name)
                    if not rag_response:
                        rag_response = f"Oi, {user.name}!" 
                    response_text = f"{rag_response}\n\n{TEXTS['MAIN_MENU_TEXT']}"
                else:
                    user.state = "WAITING_NAME"
                    response_text = (
                        "Olá! Sou o assistente virtual da Secretaria Municipal de Saúde.\n"
                        "Para continuar, digite apenas o seu nome:"
                    )

            elif user.state == "WAITING_NAME":
                nome = self._extract_name(clean_text)
                print("NOME EXTRAÍDO:", nome)

                if len(nome) < 2:
                    response_text = "Digite um nome válido."
                elif len(nome) > 30:
                    response_text = "Nome muito longo. Digite apenas seu primeiro nome."
                elif any(char.isdigit() for char in nome):
                    response_text = "O nome não deve conter números."
                elif len(nome.split()) > 3:
                    response_text = "Digite apenas seu primeiro nome."
                else:
                    user.name = nome
                    user.state = "WAITING_MAIN_MENU_CHOICE"
                    
                    response_text = (
                        f"Prazer, {user.name}! 😊\n"
                        "Como posso te ajudar hoje?\n\n"
                        f"{TEXTS['MAIN_MENU_TEXT']}"
                    )

            elif user.state in MENU_ROUTER:
                current_menu_option, current_menu_text = MENU_ROUTER[user.state]
                handler_function = current_menu_option.get(clean_text)

                if handler_function:
                    try:
                        response_text = handler_function(user, self.db, self.nlp)
                    except TypeError:
                        response_text = handler_function(user, self.db)
                else:
                    if clean_text.isdigit():
                        response_text = f"Opção inválida. Por favor, digite um número válido:\n\n{current_menu_text}"
                    else:
                        maintenance_mode = self.config_service.get_config("maintenance_mode", "false")
                        if maintenance_mode == "true":
                            response_text = "O Chat Bot está em manutenção."
                        else:
                            try:
                                rag_response = self.nlp.process(clean_text, user_name=user.name)
                                rag_lower = (rag_response or "").lower()
                                
                            
                                if not rag_response or "não" in rag_lower or "desculpe" in rag_lower or "sinto muito" in rag_lower:
                                    response_text = f"Opção inválida. Por favor, digite um número válido:\n\n{current_menu_text}"
                                else:
                                    response_text = f"{rag_response}\n\n{current_menu_text}"
                                    
                            except Exception as nlp_error:
                                print("erro do NLP:", str(nlp_error))
                                response_text = "Erro ao processar sua mensagem."

            elif user.state.endswith("_FLOW") and clean_text.isdigit() and len(clean_text) == 1:
                response_text = "Você está em um atendimento específico. Digite sua pergunta para mim ou envie *0* para voltar ao menu."

            else:
                maintenance_mode = self.config_service.get_config("maintenance_mode", "false")
                if maintenance_mode == "true":
                    response_text = "O Chat Bot está em manutenção."
                else:
                    try:
                        response_text = self.nlp.process(clean_text, user_name=user.name)
                        if not response_text:
                            response_text = "Não consegui entender. Pode reformular?"
                    except Exception as nlp_error:
                        print("erro do NLP:", str(nlp_error))
                        response_text = "Erro ao processar sua mensagem."

            self._save_message(chat, response_text, "bot")
            self.db.commit()

            return str(response_text)

        except Exception as e:
            self.db.rollback()
            print("ERRO REAL:", str(e))
            return "Desculpe, ocorreu um erro interno."

    def _clean_text(self, text: str) -> str:
        if ":" in text:
            text = text.split(":")[-1]
        return " ".join(text.strip().split())

    def _extract_name(self, text: str) -> str:
        nome = text
        if ":" in nome:
            nome = nome.split(":")[-1]
        nome = nome.strip()
        nome = " ".join(nome.split())
        return nome

    def _get_or_create_user(self, id_wpp: str) -> User:
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