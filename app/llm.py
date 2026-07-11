from langchain_ollama import ChatOllama


detection_llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0
)

extraction_llm = ChatOllama(
    model="qwen2.5:7b",
    temperature=0
)