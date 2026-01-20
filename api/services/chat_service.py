from api.models.models import User, Chat, Message
from api.services.nlp_service import NLPService

class ChatService:
    def __init__(self, db, nlp_service: NLPService):
        self.db = db
        self.nlp = nlp_service

    async def process_message(self, id_wpp: str, text: str) -> str:
        user = self._get_or_create_user(id_wpp)
        chat = self._get_or_create_chat(user)

        msg_user = self._save_message(chat, text, "user")

        response_text = await self.nlp.process(text)

        msg_bot = self._save_message(chat, response_text, "bot")

        self.db.commit()
        return response_text

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

        