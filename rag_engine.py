import os
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from model_manager import ModelManager

# Secure import to ensure compatibility with all versions
try:
    from langchain_classic.chains import RetrievalQA
except ImportError:
    from langchain_community.chains import RetrievalQA

class RAGEngine:
    def __init__(self, db_path="./db"):
        self.db_path = db_path
        self.embeddings = ModelManager.get_embeddings()
        self.llm = ModelManager.get_llm()
        self.vector_db = None

    def initialize_db(self, chunks_generator=None, batch_size=200):
        print(f"⚙️ Initializing DB Manager (Batch Size: {batch_size})...")
        
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
             self.vector_db = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embeddings
            )
        else:
            self.vector_db = Chroma(
                embedding_function=self.embeddings,
                persist_directory=self.db_path
            )

        if chunks_generator:
            batch = []
            count = 0
            for chunk in chunks_generator:
                batch.append(chunk)
                if len(batch) >= batch_size:
                    print(f"💾 Saving batch of {len(batch)} chunks... (Total: {count})")
                    self.vector_db.add_documents(batch)
                    batch = []
                    count += batch_size
            
            if batch:
                print(f"💾 Saving final batch of {len(batch)} chunks...")
                self.vector_db.add_documents(batch)
            print("✅ Ingestion Complete!")

    def get_qa_chain(self):
        if not self.vector_db:
            raise ValueError("Vector DB is not initialized.")

        # k=10 to ensure higher accuracy in large files
        retriever = self.vector_db.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 10, "fetch_k": 30}
        )
        
        
        prompt_template = """
        You are a professional AI research assistant.
        Your goal is to answer the user's question accurately using ONLY the provided context.
        
        Guidelines:
        1. Answer ONLY in English.
        2. If the answer is not in the context, strictly say: "I cannot find the answer in the provided documents."
        3. Do not make up information.
        4. Cite the source document names where appropriate.

        Context:
        {context}

        Question: {question}
        
        Answer:
        """
        
        PROMPT = PromptTemplate(
            template=prompt_template, input_variables=["context", "question"]
        )
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        
        return qa_chain