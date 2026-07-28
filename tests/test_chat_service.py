"""Maquina de estados do ChatService.

Roda contra sqlite em memoria com os models reais — nada de mock de sessao.
O NLPService entra como dublê: o que se testa aqui e o roteamento da conversa,
nao a qualidade da resposta do RAG.

Isto so e possivel porque chat_service deixou de importar NLPService em tempo
de execucao. Antes, importar este modulo baixava o modelo de embeddings.
"""
import asyncio
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.models.models import Base, Message, User  # noqa: E402
from api.services.chat_service import ChatService, normalizar_id_wpp  # noqa: E402
from api.services.menu_handlers import TEXTS  # noqa: E402

ID = "5577999999999"
MENU_PRINCIPAL = TEXTS["WAITING_MAIN_MENU"]["text"]


class NLPFake:
    """Devolve sempre a mesma coisa e guarda o que foi perguntado."""

    def __init__(self, resposta="resposta do RAG"):
        self.resposta = resposta
        self.perguntas = []

    def process(self, text, user_name=None):
        self.perguntas.append(text)
        if callable(self.resposta):
            return self.resposta(text)
        return self.resposta


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()


@pytest.fixture
def nlp():
    return NLPFake()


def conversa(db, nlp):
    """Devolve uma funcao que manda mensagem e retorna a ChatResponse."""
    def mandar(texto, id_wpp=ID):
        service = ChatService(db, nlp)
        return asyncio.run(service.process_message(id_wpp, texto))
    return mandar


def usuario(db, id_wpp=ID):
    return db.query(User).filter(User.id_wpp == id_wpp).first()


# --- normalizacao de id_wpp (item 7) ----------------------------------------

@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("whatsapp:+5577999999999", "5577999999999"),
        ("5577999999999", "5577999999999"),
        ("+55 77 99999-9999", "5577999999999"),
        ("5577999999999@s.whatsapp.net", "5577999999999"),
    ],
)
def test_normalizar_id_wpp(entrada, esperado):
    assert normalizar_id_wpp(entrada) == esperado


def test_mesmo_numero_por_gateways_diferentes_e_um_usuario_so(db, nlp):
    mandar = conversa(db, nlp)

    mandar("oi", id_wpp="whatsapp:+5577999999999")
    mandar("Maria", id_wpp="whatsapp:+5577999999999")
    mandar("oi", id_wpp="5577999999999")

    assert db.query(User).count() == 1
    assert usuario(db).name == "Maria"


# --- onboarding -------------------------------------------------------------

def test_primeiro_contato_pede_nome(db, nlp):
    resposta = conversa(db, nlp)("oi")

    assert "digite apenas o seu nome" in resposta.text.lower()
    assert usuario(db).state == "WAITING_NAME"


def test_nome_aceito_leva_ao_menu(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    resposta = mandar("Maria")

    assert "Prazer, Maria!" in resposta.text
    assert MENU_PRINCIPAL in resposta.text
    assert usuario(db).state == "WAITING_MAIN_MENU"


@pytest.mark.parametrize(
    "nome,trecho_do_erro",
    [
        ("M", "nome válido"),
        ("M" * 31, "muito longo"),
        ("Maria2", "não deve conter números"),
        ("Maria da Silva Souza", "apenas seu primeiro nome"),
    ],
)
def test_nome_invalido_mantem_estado(db, nlp, nome, trecho_do_erro):
    mandar = conversa(db, nlp)
    mandar("oi")
    resposta = mandar(nome)

    assert trecho_do_erro in resposta.text
    assert usuario(db).state == "WAITING_NAME"
    assert usuario(db).name is None


# --- comandos ---------------------------------------------------------------

def test_resetar_limpa_o_nome(db, nlp):
    # Item 8: antes o /resetar so mexia no state, entao o ramo NEW pulava o
    # onboarding e o nome digitado errado ficava para sempre.
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("/resetar")
    assert "reiniciada" in resposta.text.lower()
    assert usuario(db).name is None
    assert usuario(db).state == "NEW"

    assert "digite apenas o seu nome" in mandar("oi").text.lower()


def test_menu_volta_ao_principal(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")
    mandar("1")

    resposta = mandar("menu")
    assert MENU_PRINCIPAL in resposta.text
    assert usuario(db).state == "WAITING_MAIN_MENU"


def test_menu_sem_nome_pede_nome(db, nlp):
    resposta = conversa(db, nlp)("/menu")

    assert "digite apenas o seu nome" in resposta.text.lower()
    assert usuario(db).state == "WAITING_NAME"


# --- navegacao --------------------------------------------------------------

def test_opcao_valida_navega(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("1")
    assert usuario(db).state == "WAITING_1_AGENDAMENTO"
    assert TEXTS["WAITING_1_AGENDAMENTO"]["text"] in resposta.text


def test_numero_invalido_reexibe_o_menu(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("99")
    assert "Opção inválida" in resposta.text
    assert usuario(db).state == "WAITING_MAIN_MENU"


def test_estado_desconhecido_cai_no_menu_principal(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    user = usuario(db)
    user.state = "WAITING_ESTADO_QUE_NAO_EXISTE_MAIS"
    db.commit()

    mandar("oi de novo")
    assert usuario(db).state == "WAITING_MAIN_MENU"


# --- texto livre e RAG (item 5) ---------------------------------------------

def test_resposta_do_rag_vem_com_o_menu_junto(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("onde fica o CEMERF?")
    assert "resposta do RAG" in resposta.text
    assert MENU_PRINCIPAL in resposta.text


def test_rag_sem_resposta_reexibe_o_menu(db, nlp):
    nlp.resposta = None
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("qual a cor do céu?")
    assert "Opção inválida" in resposta.text


def test_resposta_com_a_palavra_desculpe_nao_e_descartada(db, nlp):
    # Item 5: a heuristica antiga procurava "desculpe" na resposta e jogava
    # fora qualquer texto que contivesse a palavra, por mais correto que fosse.
    nlp.resposta = "Desculpe a demora! O CEMERF fica na Avenida Olívia Flores, 3000."
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("onde fica o CEMERF?")
    assert "Avenida Olívia Flores" in resposta.text
    assert "Opção inválida" not in resposta.text


def test_erro_do_rag_nao_derruba_a_conversa(db, nlp):
    def explode(_):
        raise RuntimeError("Groq fora do ar")

    nlp.resposta = explode
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    resposta = mandar("onde fica o CEMERF?")
    assert "Opção inválida" in resposta.text
    assert usuario(db).state == "WAITING_MAIN_MENU"


# --- limpeza de texto (item 6) ----------------------------------------------

def test_dois_pontos_no_meio_da_pergunta_sobrevive(db, nlp):
    # Antes _clean_text cortava tudo antes do ultimo ":", entao
    # "Horário: 8 às 17" chegava ao RAG como "8 às 17".
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")
    mandar("Horário: quando abre o CEMERF?")

    assert nlp.perguntas[-1] == "Horário: quando abre o CEMERF?"


def test_espacos_sao_colapsados(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("   Maria   ")

    assert usuario(db).name == "Maria"


# --- manutencao e persistencia ----------------------------------------------

def test_modo_manutencao_bloqueia_texto_livre_mas_nao_o_menu(db, nlp):
    from api.services.config_service import ConfigService

    mandar = conversa(db, nlp)
    mandar("oi")
    mandar("Maria")

    ConfigService(db).set_config("maintenance_mode", "true")

    assert "manutenção" in mandar("onde fica o CEMERF?").text
    assert TEXTS["WAITING_1_AGENDAMENTO"]["text"] in mandar("1").text


def test_mensagem_vazia_nao_cria_usuario(db, nlp):
    resposta = conversa(db, nlp)("   ")

    assert "Pode repetir?" in resposta.text
    assert db.query(User).count() == 0


def test_pergunta_e_resposta_ficam_gravadas(db, nlp):
    mandar = conversa(db, nlp)
    mandar("oi")

    mensagens = db.query(Message).order_by(Message.id).all()
    assert [m.sender for m in mensagens] == ["user", "bot"]
    assert mensagens[0].text == "oi"
