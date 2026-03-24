from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies.dependencies import get_session
from api.services.attachment_service import AttachmentService

router = APIRouter(prefix="/images", tags=["Images"])


class ImageAnalysisOut(BaseModel):
    attachment_id: int
    status: str
    response: str


@router.post("/analyze", response_model=ImageAnalysisOut)
async def analyze_uploaded_image(
    request: Request,
    id_wpp: str = Form(...),
    image: UploadFile = File(...),
    category: str = Form(default="outro"),
    prompt: str = Form(default=""),
    db: Session = Depends(get_session),
):
    attachment_service = AttachmentService(db)
    attachment = attachment_service.save_user_attachment(
        id_wpp=id_wpp,
        upload=image,
        category=category,
        text=prompt or "Imagem enviada pelo usuario",
    )

    image_service = request.app.state.image_service
    response = image_service.process(attachment.storage_path, prompt)
    attachment.status = "analisado"
    db.commit()
    db.refresh(attachment)

    return ImageAnalysisOut(
        attachment_id=attachment.id,
        status=attachment.status,
        response=response,
    )
