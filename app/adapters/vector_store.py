from langchain_community.vectorstores import FAISS

def create_vector_store(docs, embeddings):
    return FAISS.from_documents(docs, embeddings)

def create_retriever(vector_store, k=2):
    return vector_store.as_retriever(search_kwargs={"k": k})

def get_retriever(k=2):
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": k})
