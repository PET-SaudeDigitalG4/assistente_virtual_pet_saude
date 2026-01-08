from app.core.ingestion import load_servicos
from app.adapters.splitter import split_docs

docs = load_servicos()

chunks = split_docs(docs)

for i, chunk in enumerate(chunks):
    print(f"--- Chunk {i+1} ---")
    print(chunk.page_content)
    print("\n")