# 04 — Referência da API

Base: `http://localhost:8000`. Nenhum endpoint exige autenticação hoje
(ver [doc 10](10-problemas-conhecidos.md)).

## Rotas registradas

| Método | Caminho | Origem | Arquivo |
|---|---|---|---|
| POST | `/messages/receive` | REST genérico / testes | `api/routes/routes.py` |
| POST | `/twilio/webhook` | Twilio WhatsApp | `api/routes/twilio_webhook.py` |
| POST | `/evolution_webhook` | Evolution API | `api/routes/webhook.py` |

---

## POST /messages/receive

Endpoint canônico. Recebe JSON, devolve JSON.

**Request** (`MessageSchema`):

```json
{
  "id_wpp": "5577999999999",
  "text": "menu"
}
```

| Campo | Tipo | Obrigatório |
|---|---|---|
| `id_wpp` | string | sim |
| `text` | string | sim |

**Response 200** (`MessageOut`):

```json
{
  "response": "🏥 *MENU PRINCIPAL*\nEscolha uma das opções abaixo:\n\n1️⃣ - Agendamento\n...",
  "image_url": null
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `response` | string | Texto a exibir ao usuário |
| `image_url` | string \| null | URL de imagem associada à opção, quando houver |

Erros internos não retornam 5xx: `ChatService` captura a exceção, faz rollback e
devolve 200 com `response = "Desculpe, ocorreu um erro interno."`.

---

## POST /twilio/webhook

Recebe `application/x-www-form-urlencoded` no formato do Twilio.

| Campo do form | Uso |
|---|---|
| `Body` | texto da mensagem |
| `From` | vira `id_wpp` (ex.: `whatsapp:+5577999999999`) |

**Response**: TwiML (`application/xml`). O texto passa por `xml.sax.saxutils.escape`.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>
        <Body>Prazer, Maria! 😊 ...</Body>
        <Media>https://.../vacinacao.jpeg</Media>
    </Message>
</Response>
```

O bloco `<Media>` só aparece quando `image_url` está preenchido.

> Nota: `id_wpp` aqui inclui o prefixo `whatsapp:` — o mesmo telefone chegando pela
> Evolution API vira um usuário **diferente** no banco.

---

## POST /evolution_webhook

Recebe o payload de eventos da Evolution API.

Payload esperado (recorte):

```json
{
  "event": "messages.upsert",
  "data": {
    "key": { "remoteJid": "5577999999999@s.whatsapp.net" },
    "message": { "conversation": "menu" }
  }
}
```

Extração:

- `remoteJid` → `number = remoteJid.split("@")[0]` → vira `id_wpp`
- texto: `message.conversation` ou `message.extendedTextMessage.text`

Mensagens ignoradas (retornam 200 com `status: ignored`):

| Situação | `reason` |
|---|---|
| `event` diferente de `messages.upsert` | `not a message event` |
| `remoteJid` contém `@g.us` (grupo) ou `status@broadcast` | `group or status message` |
| Sem texto | resposta `{"status": "no_text"}` |

**Envio da resposta**: diferente dos outros endpoints, aqui o backend **empurra** a
mensagem de volta pela Evolution API:

| Condição | Chamada |
|---|---|
| `image_url` preenchido | `POST {EVOLUTION_URL}/message/sendMedia/{INSTANCE}` — imagem com `caption` = texto |
| Só texto | `POST {EVOLUTION_URL}/message/sendText/{INSTANCE}` |

**Response 200**: `{"status": "success"}`
**Response 500**: `{"status": "error", "message": "<detalhe>"}`

---

## Modelos Pydantic

`api/schemas/schemas.py`:

```python
class MessageSchema(BaseModel):     # entrada
    id_wpp: str
    text: str

class MessageOut(BaseModel):        # saída HTTP
    response: str
    image_url: Optional[str] = None
```

`api/schemas/responses.py`:

```python
class ChatResponse(BaseModel):      # saída interna do ChatService
    text: str
    image_url: Optional[str] = None
```

`ChatResponse` circula entre serviços; `MessageOut` é a serialização HTTP.
