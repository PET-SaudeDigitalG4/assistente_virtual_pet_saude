from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from api.schemas.schemas import MessageSchema, MessageOut
from api.dependencies.dependencies import get_session
from api.services.chat_service import ChatService

router = APIRouter(prefix="/messages", tags=["Messages"])

@router.post("/receive", response_model=MessageOut)
async def receive_message(
    payload: MessageSchema,
    request: Request,
    db: Session = Depends(get_session),
):
    nlp_service = request.app.state.nlp_service

    service = ChatService(db, nlp_service)
    response = await service.process_message(payload.id_wpp, payload.text)

    return MessageOut(response=response.text, image_url=response.image_url)
