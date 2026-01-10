from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas import MessageSchema, MessageOut
from dependencies import get_session
from services.chat_service import ChatService

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.post("/receive", response_model=MessageOut)
async def receive_message(payload: MessageSchema, db: Session = Depends(get_session)):
    service = ChatService(db)
    response = await service.process_message(payload.id_wpp, payload.text)
    return MessageOut(response=response)

