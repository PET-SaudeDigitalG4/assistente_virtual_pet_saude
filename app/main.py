from app.adapters.splitter import split_docs
from app.core.ingestion import load_servicos
from app.adapters.embeddings import get_embeddings
from app.adapters.vector_store import create_vector_store, create_retriever

def setup_system():
    docs_servicos = load_servicos()
    
    chunks_servicos = split_docs(docs_servicos)

    embeddings = get_embeddings()

    vector_store = create_vector_store(chunks_servicos, embeddings)

    retriever = create_retriever(vector_store)

    return {"servicos": retriever}
