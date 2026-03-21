from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.services.chat_service import ChatService
from api.db.database import get_db

router = APIRouter()

@router.post("/dialogflow_webhook")
async def dialogflow_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()

        print("BODY:", body)

        user_text = body.get("queryResult", {}).get("queryText", "")
        id_wpp = body.get("session", "unknown_user")

        nlp_service = request.app.state.nlp_service
        chat_service = ChatService(db, nlp_service)

        resposta = await chat_service.process_message(id_wpp, user_text)

        return JSONResponse(
            content={
                "fulfillmentText": resposta,
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": [resposta]
                        }
                    }
                ]
            }
        )

    except Exception as e:
        print("ERRO WEBHOOK:", str(e))
        return JSONResponse(
            content={
                "fulfillmentText": "Erro interno no servidor.",
                "fulfillmentMessages": [
                    {
                        "text": {
                            "text": ["Erro interno no servidor."]
                        }
                    }
                ]
            }
        )