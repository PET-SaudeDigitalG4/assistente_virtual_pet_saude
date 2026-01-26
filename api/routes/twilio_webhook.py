from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from xml.sax.saxutils import escape

router = APIRouter()

@router.post("/twilio/webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    text = form.get("Body", "")

    service = request.app.state.nlp_service
    resposta = service.process(text)

    safe_text = escape(resposta)

    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{safe_text}</Message>
</Response>"""

    return PlainTextResponse(
        xml_response,
        media_type="application/xml"
    )
