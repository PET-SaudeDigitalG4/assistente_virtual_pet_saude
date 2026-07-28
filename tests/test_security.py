"""Autenticacao das rotas de entrada (api/security.py).

O que importa aqui e o comportamento em falha: variavel ausente, header
ausente, token errado. Todos tem que negar. Um `return True` acidental em
qualquer um desses ramos reabre a rota para o mundo inteiro.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from api.security import (  # noqa: E402
    assinatura_twilio_valida,
    token_webhook_valido,
    url_publica,
)

TOKEN = "segredo-de-teste"


# --- token_webhook_valido ---------------------------------------------------

def test_token_correto_passa(monkeypatch):
    monkeypatch.setenv("WEBHOOK_TOKEN", TOKEN)
    assert token_webhook_valido(TOKEN) is True


@pytest.mark.parametrize(
    "recebido",
    [None, "", "errado", TOKEN + "x", TOKEN[:-1], TOKEN.upper(), " " + TOKEN],
)
def test_token_diferente_e_negado(monkeypatch, recebido):
    monkeypatch.setenv("WEBHOOK_TOKEN", TOKEN)
    assert token_webhook_valido(recebido) is False


def test_sem_variavel_definida_nega_tudo(monkeypatch):
    # Falha fechado: sem segredo configurado ninguem entra, nem mandando vazio.
    monkeypatch.delenv("WEBHOOK_TOKEN", raising=False)
    assert token_webhook_valido(TOKEN) is False
    assert token_webhook_valido("") is False
    assert token_webhook_valido(None) is False


def test_variavel_vazia_nao_libera(monkeypatch):
    # "" == "" seria True numa comparacao ingenua.
    monkeypatch.setenv("WEBHOOK_TOKEN", "")
    assert token_webhook_valido("") is False


# --- assinatura_twilio_valida -----------------------------------------------

URL = "https://exemplo.test/twilio/webhook"
PARAMS = {"Body": "menu", "From": "whatsapp:+5577999999999"}


def _assinar(auth_token: str, url: str = URL, params: dict = PARAMS) -> str:
    from twilio.request_validator import RequestValidator

    return RequestValidator(auth_token).compute_signature(url, params)


def test_assinatura_correta_passa(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    assert assinatura_twilio_valida(URL, PARAMS, _assinar(TOKEN)) is True


def test_assinatura_de_outro_token_e_negada(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    assert assinatura_twilio_valida(URL, PARAMS, _assinar("outro-token")) is False


def test_corpo_adulterado_invalida_assinatura(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    assinatura = _assinar(TOKEN)
    adulterado = dict(PARAMS, Body="/resetar")
    assert assinatura_twilio_valida(URL, adulterado, assinatura) is False


def test_url_diferente_invalida_assinatura(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    assinatura = _assinar(TOKEN)
    outra = "https://exemplo.test/twilio/webhook/outro"
    assert assinatura_twilio_valida(outra, PARAMS, assinatura) is False


@pytest.mark.parametrize("assinatura", [None, ""])
def test_sem_header_de_assinatura_nega(monkeypatch, assinatura):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", TOKEN)
    assert assinatura_twilio_valida(URL, PARAMS, assinatura) is False


def test_sem_auth_token_nega(monkeypatch):
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    assert assinatura_twilio_valida(URL, PARAMS, _assinar(TOKEN)) is False


# --- url_publica ------------------------------------------------------------

def test_sem_public_base_url_usa_a_recebida(monkeypatch):
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)
    assert url_publica("http://localhost:8000/twilio/webhook", "/twilio/webhook") == (
        "http://localhost:8000/twilio/webhook"
    )


def test_public_base_url_reescreve_host_e_esquema(monkeypatch):
    # Caso real: tunel https na frente, aplicacao enxergando http://localhost.
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.exemplo.test")
    assert url_publica("http://localhost:8000/twilio/webhook", "/twilio/webhook") == (
        "https://bot.exemplo.test/twilio/webhook"
    )


def test_barra_final_na_base_nao_duplica(monkeypatch):
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.exemplo.test/")
    assert url_publica("http://localhost:8000/twilio/webhook", "/twilio/webhook") == (
        "https://bot.exemplo.test/twilio/webhook"
    )
