"""Deteccao de saudacao (app/core/intencao.py).

Substituiu uma chamada de LLM por mensagem. O erro que importa e o falso
positivo: classificar "Oi, onde fica o CEMERF?" como saudacao faz o bot
responder "Olá! Como posso ajudar?" e engolir a pergunta.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.intencao import e_saudacao, normalizar  # noqa: E402


@pytest.mark.parametrize(
    "texto",
    [
        "oi", "Oi", "OI", "olá", "Olá!", "ola",
        "bom dia", "Bom dia!", "BOA TARDE", "boa noite",
        "opa", "salve", "e aí", "tudo bem?", "tudo bem",
        "  oi  ", "oi.", "oi!!!",
    ],
)
def test_saudacoes_sao_reconhecidas(texto):
    assert e_saudacao(texto) is True


@pytest.mark.parametrize(
    "texto",
    [
        "onde fica o CEMERF?",
        "Oi, onde fica o CEMERF?",
        "bom dia, quais documentos preciso levar?",
        "quero agendar uma consulta",
        "1",
        "olá gostaria de saber sobre o CAPS",
    ],
)
def test_perguntas_nao_sao_saudacao(texto):
    assert e_saudacao(texto) is False


@pytest.mark.parametrize("texto", ["", "   ", None])
def test_vazio_nao_e_saudacao(texto):
    assert e_saudacao(texto) is False


def test_normalizar_tira_acento_e_pontuacao():
    assert normalizar("  Olá!!  ") == "ola"
    assert normalizar("BOM DIA.") == "bom dia"


def test_normalizar_colapsa_espacos():
    assert normalizar("bom     dia") == "bom dia"
