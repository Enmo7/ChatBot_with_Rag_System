import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama

class ModelManager:
    """
    Handles the initialization of the LLM and Embedding models.
    """
    
    @staticmethod
    def get_embeddings():
        """
        Initializes the local embedding model using HuggingFace.
        Using 'all-MiniLM-L6-v2' as it is lightweight and efficient for local CPU.
        """
        print("Initializing Embedding Model...")
        return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

    @staticmethod
    def get_llm(model_name="llama3.2"):
        """
        Initializes the Ollama LLM.
        Ensure 'ollama serve' is running in the background.
        """
        print(f"Initializing LLM ({model_name})...")
        return ChatOllama(model=model_name)