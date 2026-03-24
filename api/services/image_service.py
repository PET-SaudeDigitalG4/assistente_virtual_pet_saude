from app.core.image_pipeline import analyze_image


class ImageService:
    def process(self, image_path: str, prompt: str | None = None) -> str:
        return analyze_image(image_path=image_path, prompt=prompt)
