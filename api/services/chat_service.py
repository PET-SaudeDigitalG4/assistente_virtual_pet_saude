from api.models.models import User, Chat, Message
from api.services.nlp_service import NLPService
from api.utils.logger import DbLogger
from api.services.config_service import ConfigService

class ChatService:
    def __init__(self, db, nlp_service: NLPService):
        self.db = db
        self.nlp = nlp_service
        self.config_service = ConfigService(db)

    async def process_message(self, id_wpp: str, text: str) -> str:
        try:
            user = self._get_or_create_user(id_wpp)
            chat = self._get_or_create_chat(user)
            
            DbLogger.log_event(
                self.db, "INFO", "MESSAGE_RECEIVED", 
                f"Mensagem recebida de {id_wpp}", 
                user_id=user.id
            )
            
            msg_user = self._save_message(chat, text, "user")

            maintenance_mode = self.config_service.get_config("maintenance_mode", "false")
            
            if maintenance_mode == "true":
                response_text = "O Chat Bot está em manuntenção no momento."
            else:
                response_text = await self.nlp.process(text)

            msg_bot = self._save_message(chat, response_text, "bot")

            self.db.commit()
            return response_text
        
        except Exception as e:
            DbLogger.log_event(
                self.db, "ERROR", "PROCESSING_ERROR", 
                f"Erro ao processar mensagem: {str(e)}", 
                user_id=user.id if 'user' in locals() else None,
                meta={"stack_trace": str(e)}
            )
            return "Desculpe, ocorreu um erro interno."

    def send_message(self, id_wpp: str, text: str) -> str:
        user = self._get_or_create_user(id_wpp)
        chat = self._get_or_create_chat(user)

        self._save_message(chat, text, "system_push")

        self.db.commit()
        return "Mensagem enviada com sucesso"

    def _get_or_create_user(self, id_wpp: str) -> User:
        user = self.db.query(User).filter(User.id_wpp == id_wpp).first()

        if not user:
            user = User(id_wpp=id_wpp)
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
        message = Message(chat=chat, text=text, sender=sender)
        self.db.add(message)
        self.db.flush()
        return message