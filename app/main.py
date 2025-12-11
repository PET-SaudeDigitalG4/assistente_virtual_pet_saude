from app.core.ingestion import load_all_courses
from app.adapters.embeddings import get_embeddings
from app.adapters.vector_store import create_vector_store, create_retriever

def setup_system():
    cursos_docs = load_all_courses()
    embeddings = get_embeddings()

    retrievers = {}

    for curso, docs in cursos_docs.items():
        vs = create_vector_store(docs, embeddings)
        retrievers[curso] = create_retriever(vs)

    return retrievers
