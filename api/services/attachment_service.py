import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy.orm import Session

from api.models.models import Attachment, Chat, Message, User


class AttachmentService:
    def __init__(self, db: Session, storage_dir: str | None = None):
        self.db = db
        self.storage_dir = Path(storage_dir or "data/uploads")

    def save_user_attachment(
        self,
        id_wpp: str,
        upload: UploadFile,
        category: str = "outro",
        text: str | None = None,
    ) -> Attachment:
        user = self._get_or_create_user(id_wpp)
        chat = self._get_or_create_chat(user)
        message = self._create_message(chat, text) if text else None

        now = datetime.now(timezone.utc)
        suffix = Path(upload.filename or "").suffix or ".bin"
        stored_filename = f"{uuid4().hex}{suffix.lower()}"
        relative_dir = Path(str(now.year), f"{now.month:02d}")
        target_dir = self.storage_dir / relative_dir
        target_dir.mkdir(parents=True, exist_ok=True)

        target_path = target_dir / stored_filename
        upload.file.seek(0)
        with target_path.open("wb") as output_file:
            shutil.copyfileobj(upload.file, output_file)

        attachment = Attachment(
            user_id=user.id,
            chat_id=chat.id,
            message_id=message.id if message else None,
            original_filename=upload.filename or stored_filename,
            stored_filename=stored_filename,
            storage_path=str(target_path),
            mime_type=upload.content_type or "application/octet-stream",
            file_size=target_path.stat().st_size,
            category=(category or "outro").strip().lower(),
            status="recebido",
            created_at=now,
        )
        self.db.add(attachment)
        self.db.commit()
        self.db.refresh(attachment)
        return attachment

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

    def _create_message(self, chat: Chat, text: str) -> Message:
        message = Message(chat=chat, text=text, sender="user_image")
        self.db.add(message)
        self.db.flush()
        return message
