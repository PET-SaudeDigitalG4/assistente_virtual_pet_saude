from app.core.rag_pipeline import run_rag

def responder(mensagem, historico, retriever_servicos):
    return run_rag(retriever_servicos, mensagem)
