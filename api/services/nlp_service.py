from app.core.rag_pipeline import run_rag

class NLPService:
    def __init__(self, retriever):
        self.retriever = retriever

    async def process(self, text: str) -> str:
        if not text or not text.strip():
            return "Digite uma mensagem válida."

        return run_rag(
            retriever=self.retriever,
            pergunta=text
        )
