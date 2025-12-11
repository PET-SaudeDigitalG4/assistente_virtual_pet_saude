# test/test_retriever.py
from src.adapters.core.vector_store import load_vectorstore

vs = load_vectorstore()  
retriever = vs.as_retriever(search_kwargs={"k": 3})

query = "Como funciona o atendimento ambulatorial?"
docs = retriever.get_relevant_documents(query)

print("Resultados:")
for d in docs:
    print("-", d.page_content[:200], "...\n")
