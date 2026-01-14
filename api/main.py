from fastapi import FastAPI
from api.routes.routes import router
from app.main import setup_system
from api.services.nlp_service import NLPService

app = FastAPI()

pln_resources = setup_system()

nlp_service = NLPService(
    retriever=pln_resources["servicos"]
)

app.state.nlp_service = nlp_service

app.include_router(router)