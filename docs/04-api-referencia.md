# 04 — Referência da API

Base: `http://localhost:8000`.

## Rotas registradas

| Método | Caminho | Origem | Autenticação | Arquivo |
|---|---|---|---|---|
| POST | `/messages/receive` | REST genérico / testes | Header `X-Webhook-Token` | `api/routes/routes.py` |
| POST | `/twilio/webhook` | Twilio WhatsApp | Header `X-Twilio-Signature` | `api/routes/twilio_webhook.py` |
| POST | `/evolution_webhook` | Evolution API | `?token=` ou `X-Webhook-Token` | `api/routes/webhook.py` |

Toda a verificação vive em `api/security.py`, que **falha fechado**: variável de ambiente
ausente, header ausente ou token errado resultam em recusa. Nenhuma das três rotas tem
modo aberto.

| Falha | Resposta |
|---|---|
| Token ausente ou errado em `/messages/receive` | `403 {"detail": "Token invalido"}` |
| Assinatura ausente ou inválida em `/twilio/webhook` | `403 {"detail": "Assinatura Twilio invalida"}` |
| Token ausente ou errado em `/evolution_webhook` | `403 {"status": "forbidden"}` |

---

## POST /messages/receive

Endpoint canônico. Recebe JSON, devolve JSON.

**Header obrigatório**: `X-Webhook-Token: <WEBHOOK_TOKEN>`.
Sem ele a rota entregaria a mesma capacidade dos webhooks — falar como qualquer
`id_wpp` e consumir cota da Groq — sem exigir nada.

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

**Autenticação**: header `X-Twilio-Signature`, validado com `RequestValidator` do SDK
oficial contra o `TWILIO_AUTH_TOKEN`. A assinatura cobre a URL chamada **mais** todos os
campos do formulário, então alterar o `Body` ou o `From` invalida a requisição. Atrás de
túnel ou proxy, defina `PUBLIC_BASE_URL` — ver [doc 03](03-instalacao-e-execucao.md).

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

**Autenticação**: segredo compartilhado, em `?token=<WEBHOOK_TOKEN>` na URL configurada
no manager ou no header `X-Webhook-Token`. A Evolution API não assina os payloads que
envia — não há assinatura para conferir, só o segredo. Comparação com
`hmac.compare_digest`.

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
