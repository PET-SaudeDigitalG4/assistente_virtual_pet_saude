"""Migracao d2f3a4b5c6d7 — normalizacao de users.id_wpp.

Migracao que reescreve chave UNIQUE em linhas de producao. O caso perigoso e a
colisao: o mesmo cidadao existindo pelos dois gateways. Sem a guarda, o UPDATE
estoura UNIQUE e a migracao morre no meio, com parte das linhas ja alterada.
"""
import importlib.util
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

MIGRACAO = (
    RAIZ / "api" / "alembic" / "versions" / "d2f3a4b5c6d7_normaliza_id_wpp.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_id_wpp", MIGRACAO)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


migracao = _carregar_migracao()


@pytest.fixture
def bind():
    engine = create_engine("sqlite://")
    with engine.connect() as conexao:
        conexao.execute(
            text("CREATE TABLE users (id INTEGER PRIMARY KEY, id_wpp TEXT UNIQUE)")
        )
        yield conexao


def inserir(bind, *ids):
    for i, id_wpp in enumerate(ids, start=1):
        bind.execute(
            text("INSERT INTO users (id, id_wpp) VALUES (:id, :w)"),
            {"id": i, "w": id_wpp},
        )


def ids(bind):
    return sorted(r[0] for r in bind.execute(text("SELECT id_wpp FROM users")))


def test_prefixo_do_twilio_e_removido(bind):
    inserir(bind, "whatsapp:+5577999999999")
    migracao.normalizar_usuarios(bind)
    assert ids(bind) == ["5577999999999"]


def test_numero_ja_puro_fica_como_esta(bind):
    inserir(bind, "5577999999999")
    migracao.normalizar_usuarios(bind)
    assert ids(bind) == ["5577999999999"]


def test_colisao_nao_quebra_e_preserva_as_duas_linhas(bind):
    # Mesma pessoa pelos dois gateways: normalizar a primeira colidiria com a
    # segunda. A linha antiga fica intacta em vez de estourar UNIQUE.
    inserir(bind, "whatsapp:+5577999999999", "5577999999999")
    migracao.normalizar_usuarios(bind)
    assert ids(bind) == ["5577999999999", "whatsapp:+5577999999999"]


def test_varias_linhas_sem_colisao(bind):
    inserir(bind, "whatsapp:+5577111111111", "whatsapp:+5577222222222", "5577333333333")
    migracao.normalizar_usuarios(bind)
    assert ids(bind) == ["5577111111111", "5577222222222", "5577333333333"]


def test_valor_sem_digito_nenhum_e_ignorado(bind):
    inserir(bind, "whatsapp:", "5577999999999")
    migracao.normalizar_usuarios(bind)
    assert ids(bind) == ["5577999999999", "whatsapp:"]


def test_e_idempotente(bind):
    inserir(bind, "whatsapp:+5577999999999")
    migracao.normalizar_usuarios(bind)
    migracao.normalizar_usuarios(bind)
    assert ids(bind) == ["5577999999999"]
