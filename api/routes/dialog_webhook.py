from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.services.chat_service import ChatService

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

        fulfillment_messages = [
            {
                "text": {
                    "text": [resposta.text]
                }
            }
        ]

        if resposta.image_url:
            fulfillment_messages.append(
                {
                    "image": {
                        "imageUri": resposta.image_url
                    }
                }
            )

        return JSONResponse(
            content={
                "fulfillmentText": resposta.text,
                "fulfillmentMessages": fulfillment_messages,
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
                ],
            }
        )
