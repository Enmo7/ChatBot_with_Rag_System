import torch
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import ChatOllama

class ModelManager:
    """
    Configuration for English-Only High-Performance RAG.
    """
    
    @staticmethod
    def get_embeddings():
        """
        Initializes the Best English Embedding Model.
        'all-mpnet-base-v2' maps sentences to a 768 dimensional vector space 
        and offers the best quality for English retrieval tasks.
        """
        print("Initializing High-Performance English Embedding Model (all-mpnet-base-v2)...")
        
        # Check for GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"🔌 Embeddings running on: {device.upper()}")

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