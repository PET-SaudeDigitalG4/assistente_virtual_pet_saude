# 10 — Problemas Conhecidos e Dívidas Técnicas

Levantamento por leitura do código no estado atual do `main`. Ordenado por impacto.

## Bloqueadores

### ~~1. Cadeia de migrações quebrada~~ — CORRIGIDO

`f36d189f393f_merge_heads.py` apontava para a revisão `a8f3b1c2d4e5`, que não existia em
`versions/`. `alembic upgrade head` falhava com `KeyError`, e a tabela `flow_media` —
presente no ORM — não era criada em ambiente novo.

Causa: as revisões `a8f3b1c2d4e5` e `b9c4d6e7f8a1` foram apagadas por engano no commit
`f2222b4` (o mesmo refactor que trocou o roteamento de menus). Não era uma migração que
faltou ser escrita — era arquivo perdido.

Correção: restauradas a partir de `558cf66`, o commit que as criou. Preserva bancos já
carimbados em qualquer uma das duas revisões — reescrever a cadeia teria quebrado
exatamente esses. Head único de volta em `b9c4d6e7f8a1`; `alembic upgrade head` roda
limpo do zero.

O job `migracoes` do CI cobre os dois modos de falha agora: `alembic heads` (grafo) e
`alembic upgrade head` em sqlite descartável (DDL). Ver [doc 11](11-ci.md).

## Segurança

### ~~2. Webhooks sem autenticação~~ — CORRIGIDO

As três rotas de entrada aceitavam qualquer POST. Sem validação de assinatura do Twilio
nem de segredo da Evolution API, qualquer um que descobrisse a URL injetava mensagens em
nome de qualquer `id_wpp` — e consumia cota da Groq.

Correção em `api/security.py`, aplicada aos **três** endpoints:

| Rota | Verificação |
|---|---|
| `/twilio/webhook` | `RequestValidator` do SDK oficial sobre `X-Twilio-Signature` |
| `/evolution_webhook` | Segredo compartilhado (`?token=` ou `X-Webhook-Token`), `hmac.compare_digest` |
| `/messages/receive` | Mesmo segredo, via dependência `exigir_token` |

`/messages/receive` entrou junto porque não estava no relato original mas entrega
exatamente a mesma capacidade: fechar só os dois webhooks teria deixado a porta aberta
ao lado. Tudo falha fechado — variável ausente nega, nunca libera.

Coberto por `tests/test_security.py`. Ver [doc 04](04-api-referencia.md).

### ~~3. Credencial em código versionado~~ — CORRIGIDO

`api/routes/webhook.py` trazia `EVOLUTION_URL`, `INSTANCE` e `API_KEY = "masterkey"`
hardcoded. Agora vêm de `EVOLUTION_URL`, `EVOLUTION_INSTANCE` e `EVOLUTION_API_KEY`, sem
segredo default — a chave em branco falha ao enviar, em vez de tentar um valor conhecido.

> Se `masterkey` chegou a ser usada em alguma instância real da Evolution API, **rotacione**.
> O valor está no histórico do git e não sai de lá.

### ~~4. Script com efeito colateral no import~~ — CORRIGIDO

`api/services/twilio_connection.py` executava no nível do módulo: lia
`os.environ["TWILIO_ACCOUNT_SID"]` (`KeyError` se faltasse) e **enviava uma mensagem
WhatsApp de verdade** para um número fixo. Nada o importava, mas o primeiro `import`
acidental mandaria mensagem em produção.

Removido. Era o exemplo copiado da documentação da Twilio, com `content_sid` e números
fixos, sem nenhum uso no projeto — envelopar em `__main__` manteria código morto com uma
arma carregada dentro. Recuperável em `git show 8c8ad52:api/services/twilio_connection.py`
se algum dia servir de referência.

## Correção e comportamento

Todos corrigidos, cobertos por `tests/test_chat_service.py` e
`tests/test_migracao_id_wpp.py`.

### ~~5. Heurística de falha do RAG por substring~~ — CORRIGIDO

`ChatService` procurava `["desculpe", "sinto muito", "não encontrei", "não entendi",
"inválido"]` dentro da resposta para decidir se a IA falhou. Qualquer resposta correta
contendo "desculpe" era descartada e substituída por "Opção inválida".

Corrigido invertendo a responsabilidade: `NLPService.process` agora devolve `None` quando
o RAG não achou nada, e o chamador só precisa de um `if`. A frase de fallback virou a
constante `RESPOSTA_SEM_CONTEXTO` em `app/adapters/respostas.py` — módulo sem nenhum
import — usada tanto pelo `rag_prompt` que a ordena quanto pelo detector que a reconhece.
Antes eram dois literais soltos, livres para divergir.

### ~~6. `_clean_text` corta tudo antes do último `:`~~ — CORRIGIDO

`"Horário: 8 às 17"` virava `"8 às 17"`. O corte existia para remover prefixo de gateway.

Removido: `_clean_text` agora só colapsa espaços. Prefixo de gateway, se voltar, é
problema da rota — a camada que conhece o formato do gateway — e não do domínio.

### ~~7. Mesmo telefone = usuários diferentes por gateway~~ — CORRIGIDO

`normalizar_id_wpp` reduz o identificador aos dígitos na entrada do `ChatService`, então
`whatsapp:+5577999999999` e `5577999999999` viram o mesmo usuário.

Linhas já gravadas são convertidas pela migração `d2f3a4b5c6d7`. Onde a normalização
colidiria — a mesma pessoa existindo pelos dois gateways — a linha antiga fica intacta:
fundir históricos exigiria escolher qual nome e estado sobrevivem, e `id_wpp` é `UNIQUE`,
então sem a guarda a migração morreria no meio.

### ~~8. `/resetar` não reseta de fato~~ — CORRIGIDO

Voltava `state` para `NEW` mas mantinha `users.name`, e o ramo `NEW` com nome preenchido
pula o onboarding — o nome nunca podia ser corrigido. Agora limpa os dois.

### ~~9. Ramo inalcançável em `ChatService`~~ — CORRIGIDO

O bloco `elif user.state.endswith("_FLOW")` era inalcançável. Removido junto com a
reescrita de `process_message`, que passou de uma cadeia de `if/elif` de 100 linhas para
um despachante e um método por estado.

### ~~10. Envio de imagem sem tratamento de erro útil~~ — CORRIGIDO

`send_text` e `send_image` agora devolvem `bool`, verificam o status HTTP com
`raise_for_status`, têm `timeout` e logam a falha com stack trace. Falhando a imagem, a
rota **manda o texto** — o cidadão recebe a resposta mesmo sem a foto. Falhando tudo, a
rota responde 502 em vez de `{"status": "success"}` mentiroso.

O `mimetype` sai de `mimetypes.guess_type(url)` em vez do `image/png` fixo, que estava
errado para a imagem `.jpeg` configurada hoje.

### ~~11. Sem retorno de erro nas rotas~~ — CORRIGIDO

Os `print()` (`"ERRO REAL:"`, `"STATE ANTES:"`, `"NOME EXTRAÍDO:"`) viraram `logger`, e a
exceção capturada em `process_message` agora grava `MESSAGE_FAILED` em `audit_logs` com o
tipo do erro — antes o `DbLogger` só era chamado num lugar.

O status 200 com mensagem amigável foi **mantido de propósito**: a conversa não pode
quebrar para o cidadão porque a Groq caiu. O que faltava era rastro, não código de erro.

## Qualidade do RAG

### 12. Modelo de embeddings em inglês para base em português

`all-MiniLM-L6-v2` é predominantemente anglófono. Um modelo multilíngue
(`paraphrase-multilingual-MiniLM-L12-v2`, `intfloat/multilingual-e5-small`) tende a
recuperar melhor em PT-BR. Trocar exige apenas `app/adapters/embeddings.py`.

### 13. Uma chamada extra de LLM por mensagem

`classify_input` gasta uma requisição só para decidir entre `greeting` e `question`.
Uma checagem local por lista de saudações resolveria a maioria dos casos, com o LLM
como desempate.

### 14. Índice reconstruído a cada boot

Sem `FAISS.save_local` / `load_local`. Com 16 arquivos é tolerável; cresce linearmente
com a base e atrasa cada deploy.

### 15. Sem memória de conversa

`generate_response` recebe `historico` e ignora. Perguntas de acompanhamento
("e o horário dele?") não têm contexto — cada mensagem é isolada.

## Estrutura e higiene

### 16. Código morto

| Item | Situação |
|---|---|
| `app/config.py` | `API_KEY` e `BASE_DIR` não são lidos por ninguém; `BASE_DIR` aponta para caminho inexistente |
| `app/database/conn.py` | Arquivo vazio |
| `app/utils/logger.py` | Arquivo vazio |
| `api/services/nlp_service.py` | Importa `setup_system` sem usar |
| `api/dependencies/dependencies.py` | `get_session` duplica `get_db` |
| `app/test/test_retriever.py` | Importa `src.adapters.core.vector_store`, que não existe |

### 17. Cobertura de testes mínima

`app/test/` são scripts de inspeção manual (só `print`). O único teste automatizado é
`tests/test_menu_texts.py`, que valida a integridade de `menu_texts.json` (ver
[doc 11](11-ci.md)). Ainda sem cobertura para: máquina de estados do `ChatService`,
`_clean_text`, validação de nome e a cascata de `_resolve_image_url` — todos puros ou
facilmente isoláveis, mas hoje só testáveis com o import pesado de `app.main`.

### 18. Dependência faltando

`requests` é usado em `api/routes/webhook.py` e não está em `api/requirements.txt`.
Nenhum dos dois requirements tem versões fixadas — build não reprodutível.
`api/requirements.txt` lista `fastapi` duas vezes e traz `jose` além de
`python-jose[cryptography]` (pacote errado, mesmo nome de import).

### 19. Dependências instaladas e não usadas

`passlib[bcrypt]`, `bcrypt`, `python-jose`, `sqlalchemy_utils` sugerem autenticação
planejada e nunca implementada. `langchain-openai` está no requirements mas o projeto
usa Groq.

## Privacidade

### 20. Mensagens de saúde armazenadas sem política

A tabela `messages` guarda o conteúdo integral do que o cidadão escreve — potencialmente
sintomas e condições de saúde — junto de nome e telefone, sem criptografia, sem prazo de
retenção e sem rotina de expurgo. Sob a LGPD isso é dado pessoal sensível (art. 5º, II).
Definir retenção, base legal e aviso ao usuário no primeiro contato.
