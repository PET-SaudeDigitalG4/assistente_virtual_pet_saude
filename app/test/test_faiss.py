from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader

def utf8_loader(file_path):
    return TextLoader(file_path, encoding="utf-8")

loader = DirectoryLoader(
    "./data/servicos",
    glob="**/*.txt",
    loader_cls=utf8_loader
)

docs = loader.load()
print("Documentos carregados:", len(docs))

emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
db = FAISS.from_documents(docs, emb)

print("FAISS criado com sucesso!")
