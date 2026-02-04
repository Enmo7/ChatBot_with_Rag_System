# Local RAG System (Offline)

> A fully local, privacy-focused Retrieval-Augmented Generation (RAG) system.
> Use your own documents (PDFs, Scanned files, Text) to chat with an AI without sending data to the cloud.

---

## Overview | 

This project implements a **RAG System** from scratch using Python. It allows you to build a "Second Brain" for your AI model. By feeding it your private documents, the AI can answer questions based *specifically* on your data, citing sources, all while running 100% offline on your machine.

**Key Features:**

* **100% Offline:** Uses local models (Llama 3.2 via Ollama) and local vector storage.
* **Advanced Parsing:** Uses **IBM Docling** to read complex PDFs (including scanned images and tables).
* **Vector Search:** Uses **ChromaDB** to store and retrieve semantic meaning.
* **Optimized:** Efficient chunking and embedding using HuggingFace models.

---

## Architecture & Flow | 

How the system turns your documents into answers:

1.  **Ingestion (Document Loading):**
    * The system scans the `./documents` folder.
    * **Docling** converts PDFs (even scanned ones) into clean Markdown text.

2.  **Splitting (Chunking):**
    * Text is split into smaller "chunks" (e.g., 1000 characters) to fit the AI's memory.

3.  **Embedding:**
    * The **HuggingFace** model converts these chunks into numerical vectors (lists of numbers representing meaning).

4.  **Storage:**
    * Vectors are saved locally in **ChromaDB** (`./db` folder).

5.  **Retrieval & Generation (The Loop):**
    * **User asks a question.**
    * System searches ChromaDB for the most relevant chunks.
    * System sends the **Question + Relevant Chunks** to **Llama 3.2**.
    * **AI generates the answer** based *only* on the provided context.

---

## Prerequisites |

Before running the code, ensure you have the following installed:

1.  **Python 3.10+**
2.  **Ollama:** [Download Here](https://ollama.com)
    * *Required to run the LLM backend.*
3.  **Llama 3.2 Model:**
    * Run this command in your terminal: `ollama pull llama3.2`

---

## Installation | 

1.  **Clone/Download the project:**
    ```bash
    git clone https://github.com/Enmo7/ChatBot_with_Rag_System.git
    cd my_local_rag
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: The first run might take time to download Docling & OCR models).*

---

## Project Structure | 

```text
my_local_rag/
│
├── documents/           # Place your PDF/TXT files here
├── db/                  # Created automatically (Vector Database)
│
├── main.py              # The entry point (Run this file)
├── model_manager.py     # Handles LLM & Embedding initialization
├── document_loader.py   # Handles PDF parsing (Docling) & Splitting
├── rag_engine.py        # Core logic (ChromaDB + RetrievalQA Chain)
│
└── requirements.txt     # List of dependencies
```

---

## Usage | 

1. **Prepare your Data:**
   * Put your PDF or TXT files inside the `documents` folder.

2. **Run the System:**
   ```bash
   python main.py
   ```

3. **First Run (Ingestion):**
   * The system will detect new files, parse them (this takes time for PDFs), and build the database.
   * Wait until you see "System Ready!".

4. **Chat:**
   * Type your question and press Enter.
   * Type `exit` to close.

---

## Common Issues & Fixes

1. **"Ollama call failed with status code 404"**
   * Cause: You haven't downloaded the specific model yet.
   * Fix: Run `ollama pull llama3.2` in your terminal.

2. **"[WinError 1314] A required privilege is not held..."**
   * Cause: Windows permission issue when downloading Docling models for the first time.
   * Fix: Run your terminal/VS Code as Administrator for the first run only.

3. **"ModuleNotFoundError: No module named 'langchain_classic'"**
   * Fix: Ensure your `rag_engine.py` imports are correct. Use `from langchain.chains import RetrievalQA` instead of `langchain_classic`.

---

## Tech Stack

* **LLM:** Llama 3.2 (via Ollama)
* **Embeddings:** sentence-transformers/all-MiniLM-L6-v2
* **Vector DB:** ChromaDB
* **Orchestration:** LangChain
* **Parser:** IBM Docling


