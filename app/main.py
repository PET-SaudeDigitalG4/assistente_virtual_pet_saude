from app.core.ingestion import load_servicos
from app.adapters.embeddings import get_embeddings
from app.adapters.vector_store import create_vector_store, create_retriever

def setup_system():
    # Carrega apenas os documentos da pasta "servicos"
    docs_servicos = load_servicos()

    # Cria o modelo de embeddings (HuggingFace, conforme definimos antes)
    embeddings = get_embeddings()

    # Cria o vector store FAISS
    vector_store = create_vector_store(docs_servicos, embeddings)

    # Cria o retriever
    retriever = create_retriever(vector_store)

    # sistema usa apenas 1 retriever
    return {"servicos": retriever}
