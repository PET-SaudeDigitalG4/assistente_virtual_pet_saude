from fastapi import FastAPI
from api.routes.routes import router
from api.routes.image_routes import router as image_router
from api.routes.twilio_webhook import router as twilio_router
from api.routes.dialog_webhook import router as dialog_router
from app.main import setup_system
from api.services.nlp_service import NLPService
from api.services.image_service import ImageService

app = FastAPI()

pln_resources = setup_system()

app.state.nlp_service = NLPService(
    retriever=pln_resources["servicos"]
)

app.include_router(router)
app.include_router(twilio_router) 
app.include_router(dialog_router)