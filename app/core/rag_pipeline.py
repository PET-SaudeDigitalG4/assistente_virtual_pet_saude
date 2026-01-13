from typing import Any
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.retrievers import BaseRetriever

from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

from app.adapters.prompts import prompt

MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"
# MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
# MODEL_NAME = "HuggingFaceH4/zephyr-7b-beta"

CACHED_LLM = None

def get_llm() -> HuggingFacePipeline:
    global CACHED_LLM
    
    if CACHED_LLM is not None:
        return CACHED_LLM
   
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype="auto",
        device_map="auto"     
    )

    pipe = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=256,          
        do_sample=True,
        temperature=0.05,            
        repetition_penalty=1.2,      
        no_repeat_ngram_size=3,     
        return_full_text=False
    )
    
    CACHED_LLM = HuggingFacePipeline(pipeline=pipe)

    return CACHED_LLM


def build_rag_chain(retriever: BaseRetriever) -> Runnable:
    llm = get_llm()

    chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
    )

    return chain

def run_rag(retriever: BaseRetriever, pergunta: str) -> str:
    if not pergunta or not pergunta.strip():
        return "Digite uma pergunta válida."

    chain = build_rag_chain(retriever)
    
    resultado = chain.invoke(pergunta)

    if isinstance(resultado, str):
        return resultado
    
    if hasattr(resultado, "content"):
        return resultado.content

    return str(resultado)
