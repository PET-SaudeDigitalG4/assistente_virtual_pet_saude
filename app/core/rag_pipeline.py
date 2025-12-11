from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from app.adapters.prompts import prompt

llm = ChatOpenAI()

def build_rag_chain(retriever):
    chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
    )
    return chain

def run_rag(retriever, pergunta):
    chain = build_rag_chain(retriever)
    resposta = chain.invoke(pergunta)
    return resposta.content
