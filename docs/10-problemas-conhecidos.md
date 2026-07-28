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

### 5. Heurística de falha do RAG por substring

`ChatService.process_message`:

```python
palavras_de_erro_ia = ["desculpe", "sinto muito", "não encontrei", "não entendi", "inválido"]
ia_falhou = not rag_response or any(p in rag_lower for p in palavras_de_erro_ia)
```

Uma resposta correta que contenha "desculpe" é descartada e substituída por "Opção
inválida". Alternativa: comparar com a frase de fallback exata definida no
`rag_prompt`, ou fazer o RAG devolver um sinal estruturado.

### 6. `_clean_text` corta tudo antes do último `:`

`"Horário: 8 às 17"` vira `"8 às 17"`. O corte foi criado para remover prefixos de
gateway; deveria ser restrito a esse caso (ex.: prefixo `whatsapp:` no início).

### 7. Mesmo telefone = usuários diferentes por gateway

Twilio entrega `From = "whatsapp:+5577999999999"`; a Evolution API entrega
`"5577999999999"`. Como `id_wpp` é único, o mesmo cidadão vira dois registros com
estados independentes. Normalizar para E.164 na entrada.

### 8. `/resetar` não reseta de fato

Volta `state` para `NEW`, mas mantém `users.name`. Como o ramo `NEW` com nome
preenchido vai direto ao menu, o "reinício" só pula o onboarding — o nome nunca pode
ser corrigido pelo usuário.

### 9. Ramo inalcançável em `ChatService`

O bloco `elif user.state.endswith("_FLOW") ...` nunca executa: nenhum estado em
`menu_texts.json` termina em `_FLOW`, e a normalização anterior já teria movido
qualquer estado desconhecido para `WAITING_MAIN_MENU`. Código morto.

### 10. Envio de imagem sem tratamento de erro útil

`send_image` em `webhook.py` monta o `try/except`, imprime a falha e segue — o cidadão
não recebe nada e não há log de auditoria. Além disso, `mimetype="image/png"` e
`fileName="imagem.png"` são fixos, enquanto a única imagem configurada é `.jpeg`.
`send_text` não tem `try/except` nem timeout.

### 11. Sem retorno de erro nas rotas

`ChatService` engole toda exceção e devolve 200 com mensagem genérica; falha de LLM,
de banco ou de rede fica indistinguível. Os `print()` espalhados
(`"ERRO REAL:"`, `"STATE ANTES:"`, `"NOME EXTRAÍDO:"`) deveriam ser `logger` — e
`DbLogger` já existe para isso, mas só é chamado em um lugar.

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
