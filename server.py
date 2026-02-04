import os
import shutil
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Recalling our RAG files
from document_loader import DocumentLoader
from rag_engine import RAGEngine

# --- Track Settings ---
WEB_FOLDER = "./web"
UPLOAD_FOLDER = "./documents"
DB_FOLDER = "./db"
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'xlsx', 'png', 'jpg', 'jpeg', 'docx'}

# Checking for folders
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- App Setup ---
app = FastAPI(title="Local RAG System API")

# Setting up CORS (to allow the browser to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- RAG Engine Configuration --- 
# We use a global variable to store the system state
rag_system = RAGEngine(DB_FOLDER)
system_state = {"is_db_ready": False}

# Attempting to load the database at startup
if os.path.exists(DB_FOLDER) and os.listdir(DB_FOLDER):
    try:
        print("🔄 Loading existing database...")
        rag_system.initialize_db()
        system_state["is_db_ready"] = True
        print("✅ Database loaded successfully!")
    except Exception as e:
        print(f"⚠️ Could not load existing DB: {e}")

# --- Helper Functions / Models ---

class QueryRequest(BaseModel):
    query: str

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_stats_data():
    """Helper to get file list from disk"""
    docs = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'txt'
                docs.append({
                    "id": filename,
                    "name": filename,
                    "type": 'pdf' if ext == 'pdf' else 'file',
                    "size": size,
                    "chunks": "?"
                })
    return docs

# --- API Endpoints ---

@app.get("/api/status")
async def check_status():
    """Check system health"""
    if system_state["is_db_ready"]:
        return {"status": "ready", "message": "System Ready"}
    
    # If files exist but DB not built
    if os.listdir(UPLOAD_FOLDER):
        return {"status": "ready", "message": "Ready (Database Needs Refresh)"}
        
    return {"status": "initializing", "message": "Waiting for documents..."}

@app.get("/api/documents")
async def list_documents():
    """List documents and stats"""
    documents = get_file_stats_data()
    stats = {"chunks": 0, "embeddings": 0}
    
    if system_state["is_db_ready"] and rag_system.vector_db:
        # Note: Accessing private attribute _collection just for stats
        try:
            count = rag_system.vector_db._collection.count()
            stats["chunks"] = count
            stats["embeddings"] = count
        except:
            pass

    return {"documents": documents, "stats": stats}

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Handle multiple file uploads"""
    saved_count = 0
    
    for file in files:
        if allowed_file(file.filename):
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
           # Save the file to the disk
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_count += 1
            
    if saved_count > 0:
        return {"success": True, "message": f"Uploaded {saved_count} files"}
    
    return JSONResponse(status_code=400, content={"success": False, "message": "No valid files uploaded"})

@app.post("/api/refresh")
async def refresh_database():
    """Rebuild the RAG database"""
    try:
        loader = DocumentLoader(UPLOAD_FOLDER)
        
        # Enable heavy loading process (Blocking code)
        # In large applications, it is recommended to place this in the Background Task.
        chunks = loader.load_and_split()
        
        if not chunks:
            return JSONResponse(status_code=400, content={"success": False, "message": "No documents found"})
            
        rag_system.initialize_db(chunks)
        system_state["is_db_ready"] = True
        
        return {"success": True, "message": "Database rebuilt successfully"}
        
    except Exception as e:
        print(f"Error refreshing DB: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.post("/api/query")
async def query_rag(request: QueryRequest):
    """Answer user questions"""
    if not system_state["is_db_ready"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "System not ready"})
    
    try:
        qa_chain = rag_system.get_qa_chain()
        
        # --- The key change here ---
        # Some models require a "query" and some require an "input"
        # We will send both to ensure compatibility with any version
        payload = {
            "input": request.query,
            "query": request.query
        }
        
        # Running the chain
        response = qa_chain.invoke(payload)
        
        # Dealing with the difference in answer names (result vs. answer)
        # Older versions return 'result', newer versions return 'answer'
        answer = response.get('answer') or response.get('result')
        
        # Dealing with different source names (context vs source_documents)
        source_docs = response.get('context') or response.get('source_documents') or []
        
        # Source Extraction
        sources = []
        for doc in source_docs:
            # Checking for metadata
            if hasattr(doc, 'metadata'):
                src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                if src_name not in sources:
                    sources.append(src_name)
                
        return {
            "success": True,
            "answer": answer,
            "sources": sources
        }
        
    except Exception as e:
        print(f"Query Error: {e}")
        # Print the full error in the terminal to aid in tracking
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "message": f"Error: {str(e)}"})

# --- Static Files Mounting ---
# This should be the last thing to submit the frontend files.
# html=True means that going to the / link will automatically open index.html
app.mount("/", StaticFiles(directory=WEB_FOLDER, html=True), name="static")