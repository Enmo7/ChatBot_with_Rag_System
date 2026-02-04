# Local Multimodal RAG System (FastAPI Edition)

> **A private, offline, and multimodal AI assistant capable of chatting with your PDFs, Images, Excel sheets, and CSVs.**
> Built with **FastAPI**, **Llama 3.2**, **LangChain**, and **IBM Docling**.

---

## Key Features

<<<<<<< HEAD
* **100% Offline & Private:** Your data never leaves your device. Uses local LLMs (Ollama) and local Vector DB (Chroma).
* **High Performance:** Powered by **FastAPI** for an asynchronous, lightning-fast backend.
* **Multimodal Parsing:**
    * **PDFs:** Intelligent parsing with **IBM Docling** (supports scanned docs & OCR).
    * **Images:** Extracts text from PNG/JPG using OCR.
    * **Data Files:** Reads **Excel (.xlsx)** and **CSV** files as structured data.
* **Multilingual Support:** Supports **Arabic** and English (requires multilingual embedding model).
* **Modern UI:** A responsive, dark-mode frontend to manage files and chat.
=======
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
>>>>>>> fe788958bf8228ba287cafa642fd3cda490cdcc8

---

## Tech Stack

* **Backend:** Python, FastAPI, Uvicorn
* **AI Engine:** Llama 3.2 (via Ollama)
* **Orchestration:** LangChain (LCEL)
* **Vector DB:** ChromaDB
* **Embeddings:** HuggingFace (`all-MiniLM` or `multilingual-MiniLM`)
* **Parsing:** IBM Docling, Pandas, RapidOCR
* **Frontend:** HTML5, CSS3, Vanilla JavaScript

---

## Project Structure

```text
my_rag_project/
│
├── web/                 # Frontend (HTML/CSS/JS)
│   ├── index.html
│   ├── styles.css
│   └── app.js
│
├── documents/           # Uploaded files are stored here
├── db/                  # Vector Database (Auto-generated)
│
├── main.py              # Entry point (Runs the Uvicorn Server)
├── server.py            # FastAPI Backend Logic & Endpoints
├── rag_engine.py        # RAG Logic (Retrieval Chain)
├── document_loader.py   # Advanced File Parsing (Docling/Pandas)
├── model_manager.py     # Model Initialization
│
└── requirements.txt     # Dependencies
```

---

## Getting Started

### 1. Prerequisites

* **Python 3.10+** installed
* **Ollama** installed ([Download Here](https://ollama.com))
* **Pull the Model:**
  ```bash
  ollama pull llama3.2
  ```

### 2. Installation

1. **Clone the repository:**
   ```bash
   git clone <your-repo-url>
   cd my_rag_project
   ```

2. **Create a Virtual Environment (Recommended):**
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Mac/Linux:
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
   *(Note: The first run requires an internet connection to download OCR and Embedding models)*

### 3. Running the App

Run the following command to start the FastAPI server:

```bash
python main.py
```

* The server will start at `http://localhost:8000`
* The frontend will automatically be served at that URL
* Open your browser and navigate to `http://localhost:8000`

---

## Configuration (Language Support)

### Enabling Arabic Support

By default, the system might use an English-optimized embedding model. To support Arabic documents perfectly:

1. Open `model_manager.py`
2. Change the embedding model to a multilingual one:

```python
# In model_manager.py
return HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
)
```

3. Delete the `./db` folder and restart the app to rebuild the database with the new language model

---

## API Endpoints

The FastAPI backend provides these REST API endpoints:

### Health Check
```
GET /health
Returns server health status
```

### System Status
```
GET /api/status
Returns RAG system initialization status
```

### List Documents
```
GET /api/documents
Returns list of uploaded documents and statistics
```

### Upload Documents
```
POST /api/upload
Upload new documents (multipart/form-data)
Supported formats: PDF, TXT, CSV, XLSX, PNG, JPG
```

### Query System
```
POST /api/query
Query the RAG system
Body: { "query": "your question" }
```

### Refresh Database
```
POST /api/refresh
Rebuild the vector database from documents
```

### Clear Database
```
POST /api/clear
Clear the vector database
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `Ollama call failed (404)` | You haven't downloaded the LLM. Run `ollama pull llama3.2` in your terminal |
| `[WinError 1314] Privilege not held` | Windows permission issue. Run your terminal/VS Code as Administrator for the first run only |
| `Query Error: Missing keys` | Ensure your `server.py` sends both `input` and `query` keys in the payload (check the code in `rag_engine.py`) |
| Frontend shows "Demo Mode" | Make sure you are accessing `http://localhost:8000`. Clear your browser cache if `app.js` is stuck on the old port |
| `ModuleNotFoundError` | Make sure all dependencies are installed: `pip install -r requirements.txt` |
| Documents not uploading | Check that the `documents/` folder exists and has write permissions |
| Slow performance | Ensure you have at least 8GB RAM available. Consider using a smaller LLM model if needed |

---

## Usage Guide

### 1. Starting the System

```bash
python main.py
```

Wait for the message: "Uvicorn running on http://localhost:8000"

### 2. Uploading Documents

1. Open your browser to `http://localhost:8000`
2. Click the **"Upload Documents"** button
3. Select one or more files (PDF, TXT, CSV, XLSX, PNG, JPG)
4. Wait for processing to complete
5. Documents will appear in the library with chunk counts

### 3. Asking Questions

1. Once documents are uploaded, type your question in the chat box
2. Press **Enter** or click **Send**
3. The AI will search your documents and provide an answer with sources
4. Sources are displayed below each answer

### 4. Managing Documents

* **View**: All documents appear in the sidebar with statistics
* **Refresh**: Rebuild the vector database if needed
* **Clear**: Remove all documents and start fresh

---

## Supported File Formats

| Format | Extension | Features |
|--------|-----------|----------|
| **PDF** | `.pdf` | Text extraction, OCR for scanned documents, table recognition |
| **Text** | `.txt` | Direct text loading |
| **Excel** | `.xlsx`, `.xls` | Structured data extraction, all sheets |
| **CSV** | `.csv` | Comma-separated values, header detection |
| **Images** | `.png`, `.jpg`, `.jpeg` | OCR text extraction using RapidOCR |

---

## Performance Optimization

### For Better Speed:

1. **Use SSD Storage**: Store the `db/` folder on an SSD
2. **Increase RAM**: Allocate at least 8GB for the system
3. **Smaller Documents**: Break large PDFs into smaller files
4. **Batch Upload**: Upload multiple files at once for faster processing

### For Better Accuracy:

1. **High-Quality Scans**: Use 300 DPI or higher for scanned documents
2. **Clean Data**: Remove unnecessary pages from PDFs
3. **Structured Content**: Use well-formatted documents
4. **Multilingual Model**: Use the multilingual embedding model for Arabic content

---

## Architecture Overview

### Data Flow:

1. **Document Upload** → Files saved to `documents/` folder
2. **Parsing** → Docling/Pandas extract text and structure
3. **Chunking** → Text split into semantic chunks
4. **Embedding** → HuggingFace model converts chunks to vectors
5. **Storage** → ChromaDB stores vectors locally in `db/`
6. **Query** → User asks a question
7. **Retrieval** → ChromaDB finds relevant chunks
8. **Generation** → Llama 3.2 generates answer from context

### Components:

* **model_manager.py**: Initializes LLM and embeddings
* **document_loader.py**: Handles file parsing and chunking
* **rag_engine.py**: Implements retrieval and generation logic
* **server.py**: FastAPI endpoints and business logic
* **main.py**: Application entry point

---

## Security & Privacy

This system is designed for **LOCAL USE ONLY**:

* ✅ All data processing happens on your machine
* ✅ No data sent to external servers
* ✅ No internet required (after initial setup)
* ✅ Complete control over your documents

**Important Notes:**
* Do not expose the server to the internet without proper security
* Default configuration is for localhost only
* No authentication is implemented by default
* Suitable for personal/development use

---

## Advanced Configuration

### Changing the LLM Model

Edit `model_manager.py`:

```python
self.llm = Ollama(
    model="llama3.2",  # Change to any Ollama model
    temperature=0.7
)
```

Available models: `llama3.2`, `llama2`, `mistral`, `codellama`, etc.

### Adjusting Chunk Size

Edit `document_loader.py`:

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,      # Increase for longer context
    chunk_overlap=200     # Adjust overlap
)
```

### Customizing Retrieval

Edit `rag_engine.py`:

```python
retriever = self.vectorstore.as_retriever(
    search_kwargs={"k": 5}  # Number of chunks to retrieve
)
```

---

## Development

### Running in Development Mode

```bash
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Project Dependencies

Main libraries:
* `fastapi` - Modern web framework
* `uvicorn` - ASGI server
* `langchain` - LLM orchestration
* `chromadb` - Vector database
* `sentence-transformers` - Embeddings
* `docling` - PDF parsing
* `pandas` - Data file handling
* `rapidocr-onnxruntime` - OCR engine

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

Areas for improvement:
* Additional file format support
* Enhanced UI features
* Performance optimizations
* Better error handling
* Test coverage
* Documentation improvements

---

## Future Enhancements

Planned features:
- [ ] Audio file support (transcription)
- [ ] Video file support (frame extraction)
- [ ] Real-time collaboration
- [ ] Document comparison
- [ ] Export conversations
- [ ] Advanced search filters
- [ ] Cloud storage integration
- [ ] Mobile app

---

## License

MIT License - Free to use and modify

---

## Acknowledgments

* **Llama 3.2** by Meta AI
* **IBM Docling** for advanced PDF parsing
* **LangChain** for LLM orchestration
* **ChromaDB** for vector storage
* **FastAPI** for the web framework
* **Ollama** for local LLM serving

---

## Support

For issues and questions:
1. Check the Troubleshooting section
2. Review the server logs
3. Ensure all prerequisites are installed
4. Try the demo mode to isolate issues
5. Open an issue on GitHub

---

## Disclaimer

This is a local AI system for personal use. Always verify important information from the AI's responses against the original documents. The accuracy depends on document quality and the LLM model used.
