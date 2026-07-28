# 10 — Problemas Conhecidos e Dívidas Técnicas

Só o que continua **aberto**. Os itens já corrigidos saíram daqui — o histórico e o
raciocínio de cada correção estão nas mensagens de commit (`git log`).

Nenhum dos três abaixo é bug: dois são decisões conscientes de não fazer, um é decisão de
política que ainda não foi tomada.

---

## 1. Índice FAISS reconstruído a cada boot

**Situação:** sem `FAISS.save_local` / `load_local`, o índice é remontado a cada subida da
aplicação.

**Por que não foi feito:** o boot gasta o tempo carregando o modelo de embeddings, não
vetorizando. São 16 arquivos, algo em torno de 50 chunks — a vetorização é uma fração do
total, e o modelo precisaria ser carregado de qualquer forma para atender as consultas.

Persistir o índice trocaria cerca de um segundo por uma superfície de invalidação de
cache, que é fonte clássica de bug. E a falha aqui é silenciosa da pior maneira: base
editada com índice velho em disco significa o bot respondendo informação de saúde
desatualizada, sem nenhum sintoma visível.

**Quando revisitar:** se a base crescer uma ordem de grandeza. Aí o cálculo muda e a
invalidação por hash do conteúdo passa a valer o risco.

---

## 2. Sem memória de conversa

**Situação:** `generate_response` recebe `historico` e ignora. Cada mensagem é isolada, e
perguntas de acompanhamento ("e o horário dele?") não têm contexto.

**Por que não foi feito:** não é defeito, é funcionalidade ausente — e implementá-la muda
o comportamento do bot com o cidadão. Exige decisões de produto:

- quantos turnos entram no contexto;
- o que acontece quando o histórico contradiz os documentos;
- como isso convive com um `rag_prompt` que hoje proíbe qualquer coisa fora do `CONTEXTO`
  (ver [doc 06](06-rag.md)).

As mensagens já estão todas persistidas em `messages`, então a matéria-prima existe. O que
falta é a decisão.

---

## 3. Mensagens de saúde armazenadas sem política de retenção

**Situação:** a tabela `messages` guarda o conteúdo integral do que o cidadão escreve —
potencialmente sintomas e condições de saúde — junto de nome e telefone, sem criptografia,
sem prazo de retenção e sem rotina de expurgo.

Sob a LGPD isso é dado pessoal sensível (art. 5º, II), o que exige base legal específica e
tratamento mais restrito do que dado comum.

**Por que não foi feito:** é decisão de política, não de código. Precisa definir:

| Decisão | Quem responde |
|---|---|
| Base legal do tratamento | Jurídico da Secretaria |
| Prazo de retenção das mensagens | Secretaria + jurídico |
| Aviso ao cidadão no primeiro contato | Secretaria |
| Quem pode consultar o histórico e como | Secretaria + equipe técnica |

Depois disso a parte técnica é pequena: uma rotina de expurgo por idade, o texto do aviso
no onboarding e, se for o caso, anonimização do telefone após o encerramento do
atendimento.

**Enquanto isso:** vale saber que o dado está lá, em texto puro, e que qualquer cópia do
banco (dump, backup, ambiente de teste) carrega junto.
