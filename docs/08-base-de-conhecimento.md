# 08 — Base de Conhecimento

Fonte única de verdade das respostas: arquivos `.txt` em `data/servicos/`.
Nada além desses arquivos alimenta o RAG.

## Inventário

| Arquivo | Serviço |
|---|---|
| `secretaria_municipal_de_saude.txt` | Secretaria Municipal de Saúde |
| `servico_marcacoes.txt` | Marcação de consultas, exames e procedimentos (SUS) |
| `servico_cemerf.txt` | CEMERF — reabilitação física e auditiva |
| `servico_cemae.txt` | CEMAE |
| `servico_ceo.txt` | CEO — Centro de Especialidades Odontológicas |
| `servico_caps_ii_centro_atencao_psicossocial.txt` | CAPS II |
| `servico_caps_ad_iii.txt` | CAPS AD III |
| `servico_ambulatorio_saude_mental_atencao_a_adultos.txt` | Ambulatório de Saúde Mental (adultos) |
| `servico_concessao_aparelhos_auditivos.txt` | Concessão de aparelhos auditivos |
| `servico_concessao_meios_auxiliares_de_locomoção.txt` | Meios auxiliares de locomoção |
| `servico_concessao_orteses_e_proteses.txt` | Órteses e próteses |
| `servico_concessao_bolsas_ostomia_e_adjuvantes.txt` | Bolsas de ostomia e adjuvantes |
| `servico_eletrocardiograma.txt` | Eletrocardiograma |
| `servico_espirometria.txt` | Espirometria |
| `servico_programa_asma_grave.txt` | Programa Asma Grave |
| `servico_programa_oxigenoterapia_domiciliar_prolongada.txt` | Oxigenoterapia domiciliar prolongada |

16 arquivos, ~1 KB a 3 KB cada.

## Formato

Texto puro, UTF-8, estruturado por perguntas — as mesmas que aparecem nos submenus:

```
Serviço: CEMERF

O que é esse serviço?
Este serviço oferece acompanhamento clínico e terapias de reabilitação...

O que preciso fazer para ter acesso a esse serviço?
1. Dirija-se ao CEMERF com os documentos exigidos.
2. Realize atendimento inicial com o serviço social.
...

Quais os documentos necessários?
- CPF/RG
- Cartão SUS
- Comprovante de residência atualizado
...

Onde fica o CEMERF?
Avenida Olívia Flores, 3000, Bairro Candeias, https://maps.app.goo.gl/...

Quais os dias e horários de funcionamento?
Segunda a sexta-feira
07:00 às 17:00h

Quais os contatos?
Telefone: (77) 3229-3063
E-mail: cemerf.pmvc@gmail.com
```

Esse formato não é obrigatório tecnicamente, mas alinhar os títulos das seções com as
`query` de `menu_texts.json` melhora muito a recuperação — a busca é por similaridade
semântica, e pergunta próxima do texto do documento recupera melhor.

## Como adicionar ou atualizar um serviço

1. Crie/edite o `.txt` em `data/servicos/`, salvo em **UTF-8**, seguindo o padrão de
   seções acima e começando com `Serviço: <Nome>`.
2. Se o serviço vai aparecer no menu, adicione o estado correspondente em
   `api/services/menu_texts.json` (ver [doc 05](05-fluxo-conversa.md)).
3. Use como `query` de cada opção uma frase próxima do título da seção no `.txt`.
4. **Reinicie a aplicação.** O índice FAISS é construído no boot; não há recarga a
   quente nem watcher de arquivos.

## Restrições

- Só `.txt`. `DirectoryLoader` usa `glob="*.txt"` — PDF, DOCX e subpastas são ignorados.
- Encoding fixo em UTF-8; arquivo em Latin-1 aparece com mojibake (`ServiÃ§o`) na
  resposta ao cidadão.
- Sem versionamento ou data de vigência dentro dos arquivos: telefone/endereço
  desatualizado no `.txt` vira resposta errada e confiante para o cidadão. O `git log`
  do arquivo é o único histórico.

## Qualidade das respostas

O `rag_prompt` proíbe extrapolação: sem informação no contexto, o modelo deve responder
exatamente `"Desculpe, não encontrei essa informação específica nos meus documentos."`
Ou seja, **cobertura da base = cobertura do bot**. Pergunta cuja resposta não está em
nenhum `.txt` não deve ser respondida — se estiver sendo, é falha do prompt, não da base.
