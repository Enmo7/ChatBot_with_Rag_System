import os
import gc
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from model_manager import ModelManager
from metadata_store import MetadataStore
from langchain_classic.chains import RetrievalQA

class RAGEngine:
    def __init__(self, db_path="./db"):
        self.db_path = db_path
        self.embeddings = ModelManager.get_embeddings()
        self.llm = ModelManager.get_llm()
        self.vector_db = None
        self.metadata_store = MetadataStore()
    
    def initialize_db(self, chunks_generator=None, batch_size=200):
        print("⚙️ Initializing Vector Database...")
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            self.vector_db = Chroma(persist_directory=self.db_path, embedding_function=self.embeddings)
        else:
            self.vector_db = Chroma(embedding_function=self.embeddings, persist_directory=self.db_path)

        if chunks_generator:
            batch = []
            for chunk in chunks_generator:
                batch.append(chunk)
                if len(batch) >= batch_size:
                    self.vector_db.add_documents(batch)
                    batch = []
                    gc.collect()
            if batch: 
                self.vector_db.add_documents(batch)
            print("✅ Ingestion Complete! Documents indexed successfully.")

    def get_qa_chain(self):
        if not self.vector_db: 
            raise ValueError("Vector database not initialized. Call initialize_db() first.")
        
        retriever = self.vector_db.as_retriever(
            search_type="mmr",
            search_kwargs={"k": 6, "fetch_k": 20, "lambda_mult": 0.5}
        )
        
        # ✅ MISTRAL-OPTIMIZED PROMPT (follows Mistral's instruction format)
        prompt_template = """<s>[INST] You are a Traceability AI Assistant. Answer based ONLY on the provided context.

Rules:
1. Answer ONLY in English.
2. NEVER hallucinate - if context doesn't contain answer, say "I cannot answer based on available documents".
3. Always verify requirement IDs (REQ-xxx) exist in context before citing them.
4. Be precise and cite specific requirement IDs when relevant.
5. If asked about traceability coverage, reference the detected_links table data.

Context:
{context}

Question: {question} [/INST]

Answer:"""
        
        PROMPT = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
        
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )
        return qa_chain

    def enrich_sources(self, source_documents):
        enriched = []
        for doc in source_documents:
            file_hash = doc.metadata.get('file_hash')
            meta_info = {}
            if file_hash:
                sql_data = self.metadata_store.get_metadata(file_hash)
                if sql_data:
                    meta_info['upload_date'] = sql_data[2]
                    meta_info['version'] = sql_data[4]
            
            enriched.append({
                "source": os.path.basename(doc.metadata.get('source', 'Unknown')),
                "page": doc.metadata.get('page', 'N/A'),
                "links": doc.metadata.get('links', ''),
                "traceability": meta_info
            })
        return enriched