import os
import shutil
from typing import List
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from document_loader import DocumentLoader
from rag_engine import RAGEngine

WEB_FOLDER = "./web"
UPLOAD_FOLDER = "./documents"
DB_FOLDER = "./db"
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'xlsx', 'png', 'jpg', 'jpeg', 'docx'}

if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

app = FastAPI(title="Local English RAG System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_system = RAGEngine(DB_FOLDER)
system_state = {"is_db_ready": False}

# Attempt load on startup
if os.path.exists(DB_FOLDER) and os.listdir(DB_FOLDER):
    try:
        print("🔄 Loading existing database...")
        rag_system.initialize_db()
        system_state["is_db_ready"] = True
        print("✅ Database loaded!")
    except Exception as e:
        print(f"⚠️ Load DB Error: {e}")

class QueryRequest(BaseModel):
    query: str

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.get("/api/status")
async def check_status():
    if system_state["is_db_ready"]: return {"status": "ready", "message": "System Ready"}
    if os.listdir(UPLOAD_FOLDER): return {"status": "ready", "message": "Ready (Needs Refresh)"}
    return {"status": "initializing", "message": "Waiting for documents..."}

@app.get("/api/documents")
async def list_documents():
    docs = []
    if os.path.exists(UPLOAD_FOLDER):
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'txt'
                
                # Count chunks safely
                chunks_count = "?"
                if system_state["is_db_ready"] and rag_system.vector_db:
                    try:
                        coll = rag_system.vector_db._collection
                        ids = coll.get(where={"source": file_path})['ids']
                        if not ids: # Try alternate slash
                             ids = coll.get(where={"source": file_path.replace("\\", "/")})['ids']
                        chunks_count = len(ids)
                    except: pass

                docs.append({
                    "id": filename, "name": filename, "type": 'pdf' if ext == 'pdf' else 'file',
                    "size": size, "chunks": chunks_count
                })
    return {"documents": docs, "stats": {}}

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    saved_count = 0
    for file in files:
        if allowed_file(file.filename):
            file_path = os.path.join(UPLOAD_FOLDER, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            saved_count += 1
    if saved_count > 0: return {"success": True, "message": f"Uploaded {saved_count} files"}
    return JSONResponse(status_code=400, content={"success": False, "message": "No valid files"})

@app.post("/api/refresh")
async def refresh_database():
    try:
        loader = DocumentLoader(UPLOAD_FOLDER)
        # Use Generator for massive files
        chunks_gen = loader.process_file_generator()
        # Batch ingest
        rag_system.initialize_db(chunks_generator=chunks_gen, batch_size=200)
        
        system_state["is_db_ready"] = True
        return {"success": True, "message": "Database rebuilt successfully"}
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

@app.post("/api/query")
async def query_rag(request: QueryRequest):
    if not system_state["is_db_ready"]:
        return JSONResponse(status_code=400, content={"success": False, "message": "System not ready"})
    try:
        qa_chain = rag_system.get_qa_chain()
        payload = {"input": request.query, "query": request.query}
        response = qa_chain.invoke(payload)
        
        answer = response.get('answer') or response.get('result')
        source_docs = response.get('context') or response.get('source_documents') or []
        
        sources = []
        for doc in source_docs:
            if hasattr(doc, 'metadata'):
                src_name = os.path.basename(doc.metadata.get('source', 'Unknown'))
                if src_name not in sources: sources.append(src_name)
                
        return {"success": True, "answer": answer, "sources": sources}
    except Exception as e:
        print(f"Query Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

app.mount("/", StaticFiles(directory=WEB_FOLDER, html=True), name="static") 