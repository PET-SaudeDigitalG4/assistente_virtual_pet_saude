from app.core.rag_pipeline import run_rag
from app.main import setup_system
class NLPService:
    def __init__(self, retriever):
        self.retriever = retriever

    def process(self, text: str) -> str:
        if not text or not text.strip():
            return "Digite uma mensagem válida."

        return run_rag(
            retriever=self.retriever,
            question=text
        )
