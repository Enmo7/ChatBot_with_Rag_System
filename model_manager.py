import os
import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

class ModelManager:
    """
    Configuration for English-Only High-Performance RAG.
    Auto-detects GPU/CPU.
    """
    
    @staticmethod
    def get_embeddings():
        """
        Initializes the Best English Embedding Model (all-mpnet-base-v2).
        Automatically switches between CUDA (GPU) and CPU.
        """
        # 1. Device detection automatically
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔌 Embeddings running on: {device.upper()}")

        # 2. Download the model onto the detected device
        return HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2",
            model_kwargs={'device': device}
        )

    @staticmethod
    def get_llm(model_name="llama3.2"):
        """
        Initializes the Ollama LLM.
        """
        print(f"Initializing LLM ({model_name})...")
        return ChatOllama(model=model_name, temperature=0.1)