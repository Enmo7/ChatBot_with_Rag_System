import os
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

class ModelManager:
    @staticmethod
    def get_embeddings():
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔌 Embeddings running on: {device.upper()}")
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={'device': device}
        )
    
    @staticmethod
    def get_llm(model_name="mistral:instruct"):  # ✅ Switched to Mistral Instruct (best for RAG)
        print(f"🧠 Initializing Mistral LLM ({model_name})...")
        return ChatOllama(
            model=model_name,
            temperature=0.1,      # Low temp for factual accuracy
            num_ctx=8192,         # Mistral supports 8K context
            num_predict=512       # Reasonable response length
        )