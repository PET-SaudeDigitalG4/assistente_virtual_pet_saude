from typing import Any
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.retrievers import BaseRetriever

from langchain_huggingface import HuggingFacePipeline
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

from app.adapters.prompts import prompt


def get_llm(model_name: str = "HuggingFaceH4/zephyr-7b-beta") -> HuggingFacePipeline:
   
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype="auto",
        device_map="auto"     
    )

    pipe = pipeline(
        task="text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=512,
        do_sample=False,
        temperature=0.0,
    )

    return HuggingFacePipeline(pipeline=pipe)


def build_rag_chain(retriever: BaseRetriever, model_name: str = "mistralai/Mistral-7B-Instruct-v0.2") -> Runnable:
    """
    Constrói a chain RAG usando HuggingFacePipeline:
      pergunta -> retrieval -> prompt -> LLM open-source.
    """
    llm = get_llm(model_name)

    chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough(),
        }
        | prompt
        | llm
    )

    return chain


def run_rag(retriever: BaseRetriever, pergunta: str, model_name: str = "mistralai/Mistral-7B-Instruct-v0.2") -> str:
    """
    Executa a chain RAG usando modelo open-source do Hugging Face.
    Retorna apenas o texto final.
    """
    if not pergunta or not pergunta.strip():
        raise ValueError("A pergunta não pode estar vazia.")

    chain = build_rag_chain(retriever, model_name=model_name)

    resultado = chain.invoke(pergunta)

    # HuggingFacePipeline retorna string diretamente
    if isinstance(resultado, str):
        return resultado

    # fallback para casos atípicos
    if hasattr(resultado, "content"):
        return resultado.content

    return str(resultado)
