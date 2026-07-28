# 03 — Instalação e Execução

## Pré-requisitos

- Python 3.10+
- PostgreSQL (local ou via Docker)
- Chave de API da Groq (https://console.groq.com)
- Docker + Docker Compose — apenas se for usar o gateway Evolution API
- Conexão à internet no primeiro boot (download do modelo de embeddings do HuggingFace)

## 1. Dependências

Dois arquivos de requirements, ambos necessários para rodar o backend completo:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r api/requirements.txt
pip install -r app/requirements.txt
```

| Arquivo | Principais pacotes |
|---|---|
| `api/requirements.txt` | fastapi, uvicorn, sqlalchemy, alembic, psycopg2-binary, pydantic, twilio, python-dotenv, passlib, python-jose |
| `app/requirements.txt` | langchain (+community/core/openai), langchain_groq, faiss-cpu, sentence-transformers, transformers, huggingface-hub, gradio |

`api/requirements.txt` não lista `requests`, usado por `api/routes/webhook.py`.
Instale explicitamente se ainda não vier como dependência transitiva:

```powershell
pip install requests
```

## 2. Variáveis de ambiente

Crie um `.env` na **raiz do projeto** (já está no `.gitignore`):

```ini
# Banco da aplicação
DATABASE_URL=postgresql://usuario:senha@localhost:5432/pet_saude

# LLM
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx

# Autenticação das rotas de entrada — obrigatório
WEBHOOK_TOKEN=<segredo longo e aleatório>

# Twilio (apenas se usar o gateway Twilio)
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx
# Só se a aplicação estiver atrás de túnel/proxy (a Twilio assina a URL pública)
PUBLIC_BASE_URL=https://seu-host-publico

# Evolution API (apenas se usar esse gateway)
EVOLUTION_URL=http://localhost:8080
EVOLUTION_INSTANCE=meu-wpp
EVOLUTION_API_KEY=<apikey da sua instância>

# Postgres do docker-compose (Evolution API)
POSTGRES_USER=evolution
POSTGRES_PASSWORD=troque-me
POSTGRES_DB=evolution

# Fallback opcional de imagens de fluxo
FLOW_IMAGE_CALENDARIO=https://.../vacinacao.jpeg
```

| Variável | Onde é lida | Obrigatória |
|---|---|---|
| `DATABASE_URL` | `api/db/database.py`, `api/alembic/env.py` | Sim |
| `GROQ_API_KEY` | `app/core/rag_pipeline.py` | Sim |
| `WEBHOOK_TOKEN` | `api/security.py` | **Sim** — sem ela, `/evolution_webhook` e `/messages/receive` recusam tudo |
| `TWILIO_AUTH_TOKEN` | `api/security.py` | Só para Twilio — valida a assinatura |
| `PUBLIC_BASE_URL` | `api/security.py` | Só para Twilio atrás de túnel/proxy |
| `EVOLUTION_URL` / `EVOLUTION_INSTANCE` / `EVOLUTION_API_KEY` | `api/routes/webhook.py` | Só para Evolution |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `docker-compose.yaml` | Só para Evolution |
| `FLOW_IMAGE_<CHAVE>` | `api/services/menu_handlers.py` | Não |
| `API_KEY` | `app/config.py` (declarada, não usada) | Não |

> As rotas de entrada **falham fechado**: variável de ambiente ausente significa negar,
> nunca liberar. Sem `WEBHOOK_TOKEN` a aplicação sobe normalmente, mas todo POST em
> `/evolution_webhook` e `/messages/receive` responde 403. Ver [doc 04](04-api-referencia.md).

Gerar um `WEBHOOK_TOKEN`:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 3. Migrações

Rodar a partir do diretório `api/` (o `env.py` importa `models.models`, que só resolve
com o `api/` no `sys.path`):

```powershell
cd api
alembic upgrade head
cd ..
```

A cadeia é ramificada (dois ramos a partir de `725740865e73`, reunidos por um merge) e
termina no head `d2f3a4b5c6d7`. `alembic upgrade head` cria as 7 tabelas e insere o seed
da imagem `CALENDARIO` em `flow_media`. Ver [doc 07](07-banco-de-dados.md).

## 4. Subir o backend

Da **raiz do projeto** (os imports são absolutos: `api.*` e `app.*`):

```powershell
uvicorn api.main:app --reload
```

O primeiro boot demora: baixa `sentence-transformers/all-MiniLM-L6-v2` e constrói o
índice FAISS. Docs interativas em http://localhost:8000/docs.

## 5. Gateway WhatsApp

### Opção A — Evolution API (self-hosted)

```powershell
docker compose up -d
```

Serviços do `docker-compose.yaml`:

| Serviço | Container | Porta |
|---|---|---|
| `api` | `evolution_api` | 127.0.0.1:8080 |
| `frontend` | `evolution_frontend` (manager web) | 3000 |
| `redis` | `evolution_redis` | interno |
| `evolution-postgres` | `evolution_postgres` | interno |

Depois: abra o manager em http://localhost:3000, crie a instância, leia o QR Code e
configure o webhook.

> ⚠️ **A URL do webhook precisa carregar o token:**
>
> ```
> http://<host>:8000/evolution_webhook?token=<WEBHOOK_TOKEN>
> ```
>
> A Evolution API não assina os payloads que envia, então o segredo compartilhado é a
> única forma de distinguir o gateway de qualquer um que descubra a URL. Sem o
> `?token=`, a rota responde 403 e **o bot fica mudo**. Quem preferir header a query
> string pode configurar `X-Webhook-Token` — a rota aceita os dois.

Conexão com a Evolution API, via `.env`:

| Variável | Default | O que é |
|---|---|---|
| `EVOLUTION_URL` | `http://localhost:8080` | Onde a Evolution API escuta |
| `EVOLUTION_INSTANCE` | `meu-wpp` | Nome da instância criada no manager |
| `EVOLUTION_API_KEY` | vazio | `apikey` da instância, usada para **enviar** mensagens |

### Opção B — Twilio

Configure o Sandbox/número WhatsApp no console da Twilio para chamar
`POST https://<seu-host>/twilio/webhook`. Para expor local, use um túnel
(ngrok, cloudflared).

Aqui não há token na URL: a Twilio assina cada requisição no header
`X-Twilio-Signature`, e a rota valida essa assinatura com o `TWILIO_AUTH_TOKEN`.

A assinatura cobre a **URL exata** que a Twilio chamou. Atrás de túnel, a aplicação
enxerga `http://localhost:8000/...` enquanto a Twilio assinou `https://...`, e a
validação falha com 403. Defina `PUBLIC_BASE_URL=https://seu-host-publico` para corrigir.

## 6. Interface de teste (sem WhatsApp)

```powershell
python frontend/gradio_app.py
```

Sobe um `gr.ChatInterface` que chama o RAG direto (`generate_response`). **Não** passa
pela máquina de estados nem pelo banco — serve para testar qualidade de resposta do RAG.

Alternativa por HTTP — exige o `WEBHOOK_TOKEN`:

```powershell
curl -X POST http://localhost:8000/messages/receive `
  -H "Content-Type: application/json" `
  -H "X-Webhook-Token: $env:WEBHOOK_TOKEN" `
  -d '{"id_wpp":"5577999999999","text":"menu"}'
```

## Ordem de subida recomendada

1. PostgreSQL no ar e `DATABASE_URL` válido
2. `alembic upgrade head`
3. `uvicorn api.main:app`
4. Gateway (Evolution ou Twilio) apontando para o webhook
