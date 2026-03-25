import json
import os

diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_json = os.path.join(diretorio_atual, 'menu_texts.json')

with open(caminho_json, 'r', encoding='utf-8') as file:
    TEXTS = json.load(file)

def handle_voltar_menu_principal(user, db) -> str:
    user.state = "WAITING_MAIN_MENU_CHOICE"
    return TEXTS['MAIN_MENU_TEXT']

def handle_abrir_triagem(user, db):
    user.state = "TRIAGEM_FLOW"
    return (
        "Você escolheu 📋 *Triagem para Agendamento*.\nPor favor, digite qual especialidade você busca (ex: tomografia):\n\n"
        "*Digite 0 a qualquer momento para voltar ao menu principal*"
        )

def handle_abrir_farmacia(user, db) -> str:
    user.state = "WAITING_FARMACIA_CHOICE"
    return TEXTS['FARMACIA_MENU_TEXT']

def handle_abrir_vacinacao(user, db) -> str:
    user.state = "WAITING_VACINACAO_CHOICE"
    return TEXTS['VACINACAO_MENU_TEXT']

def handle_abrir_servicos_rede(user, db) -> str:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"
    return TEXTS['SERVICOS_REDE_MENU_TEXT']

def handle_farm_sus(user, db, nlp_service) -> str:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS['QUERIES_RAG']['REMEDIOS']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*" 

def handle_farm_rede(user, db, nlp_service) -> str:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS['QUERIES_RAG']['FARM_POPULAR']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_farm_orientacoes(user, db, nlp_service) -> str:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS['QUERIES_RAG']['ORIENTACOES']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_vac_calendario(user, db, nlp_service) -> str:
    user.state = "WAITING_FARMACIA_CHOICE"

    query = TEXTS['QUERIES_RAG']['CALENDARIO']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_vac_insumos(user, db, nlp_service) -> str:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS['QUERIES_RAG']['INSUMOS']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_vac_sesab(user, db, nlp_service) -> str:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS['QUERIES_RAG']['PROTOCOLO']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_vac_componentes(user, db, nlp_service) -> str:
    user.state = "WAITING_VACINACAO_CHOICE"

    query = TEXTS['QUERIES_RAG']['COMP_ESPECIALIZADOS']
    rag_answer = nlp_service.process(query)

    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_servicos_cemae(user, db, nlp_service) -> str:
    user.state = "WAITING_SERVICOS_REDE_CHOICE" 
    
    query = TEXTS['QUERIES_RAG']['CEMAE']
    rag_answer = nlp_service.process(query)
    
    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_servicos_cemerf(user, db, nlp_service) -> str:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"
    
    query = TEXTS['QUERIES_RAG']['CEMERF']
    rag_answer = nlp_service.process(query)
    
    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

def handle_servicos_acesso(user, db, nlp_service) -> str:
    user.state = "WAITING_SERVICOS_REDE_CHOICE"
    
    query = TEXTS['QUERIES_RAG']['ACESSO_SERVICOS']
    rag_answer = nlp_service.process(query)
    
    return f"{rag_answer}\n\n*(Escolha outra opção do menu ou digite 0 para voltar ao início)*"

MAIN_MENU_OPTIONS = {
    "1": handle_abrir_triagem,
    "2": handle_abrir_farmacia,
    "3": handle_abrir_vacinacao,
    "4": handle_abrir_servicos_rede
}

FARMACIA_MENU_OPTIONS = {
    "1": handle_farm_sus,
    "2": handle_farm_rede,
    "3": handle_farm_orientacoes,
    "0": handle_voltar_menu_principal
}

VACINACAO_MENU_OPTIONS = {
    "1": handle_vac_calendario,
    "2": handle_vac_insumos,
    "3": handle_vac_sesab,
    "4": handle_vac_componentes,
    "0": handle_voltar_menu_principal
}

SERVICOS_REDE_MENU_OPTIONS = {
    "1": handle_servicos_cemae,
    "2": handle_servicos_cemerf,
    "3": handle_servicos_acesso,
    "0": handle_voltar_menu_principal
}

MENU_ROUTER = {
    "WAITING_MAIN_MENU_CHOICE": (MAIN_MENU_OPTIONS, TEXTS['MAIN_MENU_TEXT']),
    "WAITING_FARMACIA_CHOICE": (FARMACIA_MENU_OPTIONS, TEXTS['FARMACIA_MENU_TEXT']),
    "WAITING_VACINACAO_CHOICE": (VACINACAO_MENU_OPTIONS, TEXTS['VACINACAO_MENU_TEXT']),
    "WAITING_SERVICOS_REDE_CHOICE": (SERVICOS_REDE_MENU_OPTIONS, TEXTS['SERVICOS_REDE_MENU_TEXT'])
}