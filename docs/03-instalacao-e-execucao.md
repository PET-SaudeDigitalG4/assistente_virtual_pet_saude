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

# Twilio (apenas se usar o gateway Twilio)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxx

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
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | `api/services/twilio_connection.py` | Só para Twilio |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `docker-compose.yaml` | Só para Evolution |
| `FLOW_IMAGE_<CHAVE>` | `api/services/menu_handlers.py` | Não |
| `API_KEY` | `app/config.py` (declarada, não usada) | Não |

## 3. Migrações

Rodar a partir do diretório `api/` (o `env.py` importa `models.models`, que só resolve
com o `api/` no `sys.path`):

```powershell
cd api
alembic upgrade head
cd ..
```

> ⚠️ A migração de merge `f36d189f393f` referencia a revisão `a8f3b1c2d4e5`, que **não
> existe** em `api/alembic/versions/`. `alembic upgrade head` falha nesse estado.
> Ver [doc 10 — Problemas Conhecidos](10-problemas-conhecidos.md).

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
configure o webhook apontando para `http://<host>:8000/evolution_webhook`.

Os valores de conexão com a Evolution API estão **hardcoded** em
`api/routes/webhook.py`:

```python
EVOLUTION_URL = "http://localhost:8080"
INSTANCE = "meu-wpp"
API_KEY = "masterkey"
```

Ajuste-os para o seu ambiente (ou externalize para `.env`).

### Opção B — Twilio

Configure o Sandbox/número WhatsApp no console da Twilio para chamar
`POST https://<seu-host>/twilio/webhook`. Para expor local, use um túnel
(ngrok, cloudflared).

## 6. Interface de teste (sem WhatsApp)

```powershell
python frontend/gradio_app.py
```

Sobe um `gr.ChatInterface` que chama o RAG direto (`generate_response`). **Não** passa
pela máquina de estados nem pelo banco — serve para testar qualidade de resposta do RAG.

Alternativa por HTTP:

```powershell
curl -X POST http://localhost:8000/messages/receive `
  -H "Content-Type: application/json" `
  -d '{"id_wpp":"5577999999999","text":"menu"}'
```

## Ordem de subida recomendada

1. PostgreSQL no ar e `DATABASE_URL` válido
2. `alembic upgrade head`
3. `uvicorn api.main:app`
4. Gateway (Evolution ou Twilio) apontando para o webhook
