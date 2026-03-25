from app.core.rag_pipeline import run_rag
from app.main import setup_system

class NLPService:
    def __init__(self, retriever):
        self.retriever = retriever

    def process(self, text: str, user_name: str = None) -> str:
        if not text or not text.strip():
            return "Digite uma mensagem válida."

        rag_response = run_rag(
            retriever=self.retriever,
            question=text
        )

        if user_name:
            if "Olá! Sou o assistente virtual da Secretaria Municipal de Saúde de Vitória da Conquista" in rag_response:
                rag_response = f"Oi, {user_name}! 😊\nComo posso te ajudar?"
            elif "Olá!" in rag_response:
                rag_response = rag_response.replace("Olá!", f"Oi, {user_name}! 😊")

        return rag_response