import os
from typing import Any
from dotenv import load_dotenv
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.retrievers import BaseRetriever
from langchain_core.output_parsers import StrOutputParser 
from langchain_groq import ChatGroq 
from app.adapters.prompts import *

load_dotenv()

MODEL_NAME = "llama-3.3-70b-versatile" 

CACHED_LLM = None

def get_llm() -> ChatGroq:
    global CACHED_LLM
    
    if CACHED_LLM is not None:
        return CACHED_LLM
    
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("A chave da API Groq não foi encontrada. Defina a variável de ambiente GROQ_API_KEY.")

    llm = ChatGroq(
        model=MODEL_NAME,
        temperature=0.1, 
        max_tokens=500,
        api_key=api_key
    )
    
    CACHED_LLM = llm
    return CACHED_LLM

def classify_input(llm, text: str) -> str:
    chain = intent_prompt | llm | StrOutputParser()
    result = chain.invoke({"input": text})
    return result.strip().lower()

def greeting_response(llm) -> str:
    chain = greeting_prompt | llm | StrOutputParser()
    return chain.invoke({}).strip()

def build_rag_chain(retriever: BaseRetriever) -> Runnable:
    llm = get_llm()

    chain = (
        {
            "context": retriever,
            "question": RunnablePassthrough(),
        }
        | rag_prompt
        | llm
        | StrOutputParser() 
    )

    return chain

def run_rag(retriever: BaseRetriever, question: str) -> str:
    if not question or not question.strip():
        return "Digite uma pergunta válida."

    llm = get_llm()
    
    intent = classify_input(llm, question)

    if "greeting" in intent: 
        return greeting_response(llm)

    chain = build_rag_chain(retriever)

    return chain.invoke(question)