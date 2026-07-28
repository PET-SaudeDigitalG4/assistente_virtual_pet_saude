"""Integridade do menu dinamico (api/services/menu_texts.json).

O menu e dado, nao codigo: um next_state com typo so aparece quando o cidadao
cai num beco sem saida no WhatsApp. Este teste roda antes disso.
"""
import json
from pathlib import Path

import pytest

MENU_PATH = Path(__file__).resolve().parents[1] / "api" / "services" / "menu_texts.json"

# Chaves do JSON que nao sao estados da maquina de estados.
NON_STATE_KEYS = {"FLOW_IMAGE_URLS"}

# Estados criados pelo ChatService, nao pelo JSON.
CODE_ONLY_STATES = {"NEW", "WAITING_NAME"}

TEXTS = json.loads(MENU_PATH.read_text(encoding="utf-8"))
STATES = {k: v for k, v in TEXTS.items() if k not in NON_STATE_KEYS}


def test_menu_json_e_valido():
    assert STATES, "nenhum estado encontrado em menu_texts.json"


def test_menu_principal_existe():
    # ChatService cai em WAITING_MAIN_MENU para qualquer estado desconhecido.
    assert "WAITING_MAIN_MENU" in STATES


@pytest.mark.parametrize("state", sorted(STATES))
def test_estado_tem_texto_e_opcoes(state):
    data = STATES[state]
    assert data.get("text"), f"{state} sem 'text'"
    assert isinstance(data.get("options"), dict), f"{state} sem 'options'"
    assert data["options"], f"{state} com 'options' vazio"


@pytest.mark.parametrize("state", sorted(STATES))
def test_opcao_tem_exatamente_um_comportamento(state):
    for choice, option in STATES[state]["options"].items():
        tem = [k for k in ("next_state", "query") if k in option]
        assert len(tem) == 1, (
            f"{state}[{choice}] deve ter exatamente um de next_state/query, tem {tem}"
        )


@pytest.mark.parametrize("state", sorted(STATES))
def test_next_state_aponta_para_estado_existente(state):
    for choice, option in STATES[state]["options"].items():
        alvo = option.get("next_state")
        if alvo is None:
            continue
        assert alvo in STATES or alvo in CODE_ONLY_STATES, (
            f"{state}[{choice}] aponta para estado inexistente: {alvo}"
        )


def test_todo_estado_e_alcancavel():
    alcancaveis = {"WAITING_MAIN_MENU"}
    for data in STATES.values():
        for option in data["options"].values():
            if "next_state" in option:
                alcancaveis.add(option["next_state"])

    orfaos = set(STATES) - alcancaveis
    assert not orfaos, f"estados inalcancaveis pelo menu: {sorted(orfaos)}"


@pytest.mark.parametrize("state", sorted(STATES))
def test_submenu_permite_voltar(state):
    # Sem uma saida "0", o usuario fica preso no submenu ate digitar /menu.
    if state == "WAITING_MAIN_MENU":
        return
    assert "0" in STATES[state]["options"], f"{state} nao tem opcao 0 para voltar"


def test_image_key_tem_fallback_declarado():
    # Niveis 1-3 da cascata vivem no banco/ambiente; o JSON e o ultimo fallback.
    # Se a chave nao estiver aqui, a imagem some quando banco e env estao vazios.
    fallbacks = TEXTS.get("FLOW_IMAGE_URLS", {})
    usadas = {
        option["image_key"]
        for data in STATES.values()
        for option in data["options"].values()
        if "image_key" in option
    }
    faltando = usadas - set(fallbacks)
    assert not faltando, f"image_key sem fallback em FLOW_IMAGE_URLS: {sorted(faltando)}"
