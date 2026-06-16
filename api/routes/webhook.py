import requests
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.services.chat_service import ChatService

router = APIRouter()

EVOLUTION_URL = "http://localhost:8080" 
INSTANCE = "meu-wpp"                  
API_KEY = "masterkey"                 

def send_text(number: str, text: str):
    url = f"{EVOLUTION_URL}/message/sendText/{INSTANCE}"
    requests.post(
        url,
        headers={"apikey": API_KEY},
        json={
            "number": number,
            "text": text
        }
    )

def send_image(number: str, image_url: str, caption: str = ""):
    url = f"{EVOLUTION_URL}/message/sendMedia/{INSTANCE}"
    
    payload = {
        "number": number,
        "mediatype": "image",
        "mimetype": "image/png",  
        "fileName": "imagem.png", 
        "media": image_url,
        "caption": caption
    }
      
    try:
        response = requests.post(
            url,
            headers={
                "apikey": API_KEY,
                "Content-Type": "application/json"
            },
            json=payload,
            timeout=15 
        )
            
    except Exception as e:
        print(f"Falha na requisição: {str(e)}")
        
@router.post("/evolution_webhook")
async def evolution_webhook(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        
        event_type = body.get("event", "")
        if event_type and "messages.upsert" not in event_type:
             return JSONResponse(content={"status": "ignored", "reason": "not a message event"})
        
        data = body.get("data", {})
        key = data.get("key", {}) if "key" in data else data.get("message", {}).get("key", {})
        remote_jid = key.get("remoteJid", "")
        
        if not remote_jid or "@g.us" in remote_jid or "status@broadcast" in remote_jid:
            return JSONResponse(content={"status": "ignored", "reason": "group or status message"})

        number = remote_jid.split("@")[0]
        
        message_data = data.get("message", {})
        message = message_data.get("conversation") or message_data.get("extendedTextMessage", {}).get("text", "")

        if not message:
            return JSONResponse(content={"status": "no_text"})

        nlp_service = request.app.state.nlp_service
        chat_service = ChatService(db, nlp_service)
        
        resposta = await chat_service.process_message(number, message)

        if resposta.image_url:
            send_image(number, resposta.image_url, resposta.text)
        elif resposta.text:
            send_text(number, resposta.text)

        return JSONResponse(content={"status": "success"})

    except Exception as e:
        print("ERRO:", str(e))
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)