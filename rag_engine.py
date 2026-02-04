import os
from langchain_chroma import Chroma
from langchain_classic.chains import RetrievalQA
from model_manager import ModelManager

class RAGEngine:
    """
    Manages the Vector Database (Chroma) and the Retrieval QA Chain.
    """
    
    def __init__(self, db_path="./db"):
        self.db_path = db_path
        self.embeddings = ModelManager.get_embeddings()
        self.llm = ModelManager.get_llm()
        self.vector_db = None

    def initialize_db(self, chunks=None):
        """
        Initializes the Vector Database.
        If chunks are provided, it creates a new DB.
        If not, it attempts to load an existing DB.
        """
        if chunks:
            print("Creating new Vector Database...")
            self.vector_db = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=self.db_path
            )
        else:
            if os.path.exists(self.db_path):
                print("Loading existing Vector Database...")
                self.vector_db = Chroma(
                    persist_directory=self.db_path,
                    embedding_function=self.embeddings
                )
            else:
                raise ValueError("No existing DB found and no chunks provided.")

    def get_qa_chain(self):
        """
        Creates and returns the RetrievalQA chain.
        """
        if not self.vector_db:
            raise ValueError("Vector DB is not initialized.")

        retriever = self.vector_db.as_retriever(search_kwargs={"k": 3})
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff", # "stuff" puts all chunks into prompt
            retriever=retriever,
            return_source_documents=True
        )
        
        return qa_chain