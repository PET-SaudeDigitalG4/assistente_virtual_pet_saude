
import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT_DIR)

print("ROOT_DIR:", ROOT_DIR)
print("Conteúdo da raiz:", os.listdir(ROOT_DIR))
print("PYTHONPATH:", sys.path[:3])

from app.main import setup_system
import gradio as gr
from app.core.conversation import responder
retrievers = setup_system()

def chat_fn(mensagem, historico):
    return responder(mensagem, historico, retrievers)

interface = gr.ChatInterface(fn=chat_fn)
interface.launch()
