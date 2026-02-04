import os
import sys
from document_loader import DocumentLoader
from rag_engine import RAGEngine

def main():
    print("--- Local RAG System Initialization ---")

    # Define paths
    docs_dir = "./documents"
    db_dir = "./db"

    # Initialize modules
    loader = DocumentLoader(docs_dir)
    rag = RAGEngine(db_dir)

    # Check if we need to build the DB or load it
    # Logic: If DB folder doesn't exist, we must ingest documents.
    if not os.path.exists(db_dir) or not os.listdir(db_dir):
        print("Database not found. Starting ingestion process...")
        chunks = loader.load_and_split()
        
        if not chunks:
            print("Please add PDF or TXT files to the 'documents' folder and restart.")
            sys.exit()
            
        rag.initialize_db(chunks)
    else:
        # Load existing DB
        try:
            rag.initialize_db()
        except Exception as e:
            print(f"Error loading DB: {e}")
            sys.exit()

    # Create the QA Chain
    qa_chain = rag.get_qa_chain()
    print("\n--- System Ready! (Type 'exit' to quit) ---")

    # Interaction Loop
    while True:
        query = input("\nUser: ")
        if query.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        
        if not query.strip():
            continue

        print("AI: Thinking...")
        try:
            response = qa_chain.invoke({"query": query})
            answer = response['result']
            sources = response['source_documents']

            print(f"\nAI Answer: \n{answer}")
            
            # Optional: Print sources
            print("\n[Sources Used:]")
            for doc in sources:
                source_name = os.path.basename(doc.metadata.get('source', 'unknown'))
                print(f"- {source_name}")
                
        except Exception as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()