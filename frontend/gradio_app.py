
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

print("ROOT_DIR:", ROOT_DIR)
print("Conteúdo da raiz:", os.listdir(ROOT_DIR))
print("PYTHONPATH:", sys.path[:3])

from app.main import setup_system
import gradio as gr
from app.core.conversation import generate_response
from app.core.image_pipeline import analyze_image

retrievers = setup_system()

def chat_fn(mensagem, historico):
    return generate_response(mensagem, historico, retrievers)


def image_fn(image, prompt):
    return analyze_image(image, prompt)


with gr.Blocks() as interface:
    gr.Markdown("# Assistente Virtual PET")

    with gr.Tab("Chat"):
        gr.ChatInterface(fn=chat_fn)

    with gr.Tab("Imagens"):
        image_input = gr.Image(type="filepath", label="Envie uma imagem")
        prompt_input = gr.Textbox(
            label="Pergunta sobre a imagem",
            placeholder="Ex.: O que aparece nesta imagem?",
        )
        analyze_button = gr.Button("Analisar imagem", variant="primary")
        image_output = gr.Textbox(label="Resposta", lines=8)

        analyze_button.click(
            fn=image_fn,
            inputs=[image_input, prompt_input],
            outputs=image_output,
        )

interface.launch()
