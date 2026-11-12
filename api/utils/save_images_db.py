import sys
import os
import base64

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from api.db.database import SessionLocal 
from api.services.config_service import ConfigService

diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_imagem = os.path.join(diretorio_atual, "..", "..", "data", "images", "calendario_pessoa_idosa_2026.png")
caminho_imagem = os.path.abspath(caminho_imagem)

def processar_e_salvar():
    try:
        with open(caminho_imagem, "rb") as image_file:
            base64_string = base64.b64encode(image_file.read()).decode('utf-8')
            texto_completo = f"data:image/jpeg;base64,{base64_string}"
    except FileNotFoundError:
        print(f"Erro: A imagem não foi encontrada no caminho: {caminho_imagem}")
        return

    db = SessionLocal()
    try:
        servico = ConfigService(db)
        
        servico.set_config(
            key="flow_image.calendario", 
            value=texto_completo,
            description="Imagem em Base64 do Calendario Vacinal"
        )
        print("A imagem foi convertida e salva direto na base de dados!")
    except Exception as e:
        print(f"Erro ao salvar no banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    processar_e_salvar()