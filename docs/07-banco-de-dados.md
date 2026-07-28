# 07 — Banco de Dados

PostgreSQL, acessado via SQLAlchemy ORM. Migrações com Alembic.
Modelos em `api/models/models.py`.

## Diagrama

```mermaid
erDiagram
    users ||--o{ chats : tem
    chats ||--o{ messages : contem
    users ||--o{ audit_logs : gera
    system_configs
    flow_media
```

`system_configs` e `flow_media` não têm relacionamento — são tabelas de configuração.

## Tabelas

### `users`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK autoincrement | |
| `id_wpp` | String, **unique**, not null | Telefone só com dígitos, normalizado por `normalizar_id_wpp` |
| `name` | String, nullable | Primeiro nome informado pelo usuário |
| `state` | String, default `"NEW"` | Estado atual no menu |
| `created_at` | DateTime | |

`cascade="all, delete-orphan"` em `chats`: apagar o usuário apaga seus chats.

### `chats`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → `users.id`, not null | |
| `created_at` | DateTime | |

Na prática há **um chat por usuário**: `_get_or_create_chat` sempre pega o primeiro.

### `messages`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `chat_id` | Integer FK → `chats.id`, not null | |
| `text` | String, not null | Conteúdo |
| `sender` | String, not null | `"user"` ou `"bot"` |
| `created_at` | DateTime | |

Guarda conteúdo enviado por cidadãos sobre saúde — dado pessoal sensível, hoje sem prazo
de retenção nem rotina de expurgo. Ver [doc 10](10-problemas-conhecidos.md).

### `system_configs`

Chave-valor de configuração em runtime.

| Coluna | Tipo | Notas |
|---|---|---|
| `key` | String PK, indexada | ex.: `maintenance_mode`, `flow_image.calendario` |
| `value` | String, not null | Sempre string; `"true"`/`"false"` para flags |
| `description` | String, nullable | |
| `is_active` | Boolean, default `True` | Registros inativos são ignorados na leitura |
| `updated_at` | DateTime, `onupdate` | |

### `flow_media`

Mídias associadas a opções de menu.

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `flow_key` | String, not null, indexada | Comparado em **maiúsculas** (`CALENDARIO`) |
| `media_type` | String, default `"image"` | Só `"image"` é consultado hoje |
| `media_url` | Text, not null | |
| `caption` | Text, nullable | Coluna existe, mas não é usada no envio |
| `is_active` | Boolean, default `True` | |
| `updated_at` | DateTime, `onupdate` | Usada para ordenar (mais recente vence) |

### `audit_logs`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer PK | |
| `user_id` | Integer FK → `users.id`, nullable | |
| `level` | String, not null | `INFO`, `ERROR` |
| `event_type` | String, not null | ex.: `MESSAGE_RECEIVED` |
| `message` | Text, not null | |
| `metadata_info` | JSON, nullable | Campo livre |
| `created_at` | DateTime | |

Escrito por `api/utils/logger.py::DbLogger.log_event`, que loga no console e grava
a linha. Falha de gravação não derruba a requisição — captura a exceção, loga e faz
rollback. Hoje só há **um** ponto de chamada (`MESSAGE_RECEIVED` em `ChatService`).

## Conexão

`api/db/database.py`:

```python
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()
```

Todas as rotas usam `get_db`. Existia uma cópia idêntica chamada `get_session` em
`api/dependencies/dependencies.py`, removida — esse módulo agora só abriga `exigir_token`.

## Migrações

Diretório: `api/alembic/`. Config: `api/alembic.ini` (`script_location = %(here)s/alembic`,
`prepend_sys_path = .`). A URL vem do `.env` via `env.py`, sobrescrevendo o placeholder
do `.ini`. `compare_type=True` está ativo nos dois modos.

### Cadeia de revisões

| Revisão | Descrição | down_revision |
|---|---|---|
| `c017765344ef` | Inicial: `users`, `chats`, `messages` | — |
| `725740865e73` | `system_configs`, `audit_logs` | `c017765344ef` |
| `7f566e777933` | `users.name`, `users.state` | `725740865e73` |
| `a8f3b1c2d4e5` | `flow_media` + índice + seed da imagem `CALENDARIO` | `725740865e73` |
| `f36d189f393f` | Merge heads (no-op) | `('a8f3b1c2d4e5', '7f566e777933')` |
| `b9c4d6e7f8a1` | Recria `flow_media` e reinsere o seed, ambos idempotentes | `f36d189f393f` |
| `c7d8e9fa0b1c` | Atualiza a URL do seed `CALENDARIO` para o Supabase vigente | `b9c4d6e7f8a1` |
| `d2f3a4b5c6d7` | Normaliza `users.id_wpp` para só dígitos | `c7d8e9fa0b1c` |

Head único: `d2f3a4b5c6d7`.

A cadeia é ramificada: a partir de `725740865e73` saem dois ramos —
`7f566e777933` (colunas de `users`) e `a8f3b1c2d4e5` (`flow_media`) — reunidos pelo
merge `f36d189f393f`.

`b9c4d6e7f8a1` refaz o trabalho de `a8f3b1c2d4e5` com guardas (`inspector.get_table_names()`
antes de criar, `SELECT` antes de inserir). Existe para consertar bancos que passaram pelo
merge sem terem recebido a tabela; é no-op num banco íntegro.

> ⚠️ Não apague arquivo de `versions/`, mesmo parecendo redundante. Um merge aponta para
> os dois pais pelo id: sumindo o arquivo, `alembic upgrade head` morre com `KeyError` e
> nenhum ambiente novo sobe. Já aconteceu neste repositório, num refactor que levou duas
> revisões junto sem querer. O job `migracoes` do CI (ver [doc 11](11-ci.md)) pega isso
> antes do merge do PR.

### Comandos

```powershell
cd api
alembic current                       # revisão aplicada
alembic history --verbose             # cadeia completa
alembic revision --autogenerate -m "descricao"
alembic upgrade head
alembic downgrade -1
```

Sempre rodar a partir de `api/` — `env.py` faz `from models.models import Base`.
