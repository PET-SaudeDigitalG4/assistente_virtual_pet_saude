"""Todo `from app.x import` / `from api.x import` aponta para modulo existente.

Verificacao estatica, por leitura da AST: nao importa nada de verdade, entao
roda no CI sem LangChain, torch ou chave da Groq instalados.

Existe porque um diretorio inteiro (app/adapters) foi movido sem que nenhum
import fosse atualizado, e a suite passou inteira: nenhum teste importava
app/main.py, e o unico modo de descobrir seria subir a aplicacao. Um pacote
renomeado quebra o boot em producao e nao produz nenhum sintoma antes disso.
"""
import ast
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

PACOTES = ("app", "api")
IGNORAR = {"__pycache__", ".venv", "venv", "node_modules", ".git"}


def _fontes():
    for pacote in PACOTES:
        for caminho in (RAIZ / pacote).rglob("*.py"):
            if any(parte in IGNORAR for parte in caminho.parts):
                continue
            yield caminho


def _modulos_importados(caminho: Path):
    """Nomes de modulo internos importados por este arquivo."""
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), filename=str(caminho))

    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom):
            # Import relativo: resolvido pelo proprio Python, fora do escopo.
            if no.level or not no.module:
                continue
            if no.module.split(".")[0] in PACOTES:
                yield no.module
        elif isinstance(no, ast.Import):
            for alias in no.names:
                if alias.name.split(".")[0] in PACOTES:
                    yield alias.name


def _existe(modulo: str) -> bool:
    partes = modulo.split(".")
    base = RAIZ.joinpath(*partes)
    # Namespace package (sem __init__.py) tambem vale: e assim que app/adapters
    # e api/routes funcionam hoje.
    return base.with_suffix(".py").is_file() or base.is_dir()


FONTES = sorted(_fontes())


@pytest.mark.parametrize("caminho", FONTES, ids=lambda c: str(c.relative_to(RAIZ)))
def test_imports_internos_resolvem(caminho):
    quebrados = [m for m in _modulos_importados(caminho) if not _existe(m)]

    assert not quebrados, (
        f"{caminho.relative_to(RAIZ)} importa modulo inexistente: {quebrados}"
    )


def test_encontrou_arquivos_para_verificar():
    # Sem isto, um erro no rglob deixaria a suite verde sem verificar nada.
    assert len(FONTES) > 10
