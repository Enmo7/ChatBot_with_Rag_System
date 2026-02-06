import os
import shutil
import asyncio
import aiofiles
import html
from typing import List
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Security & Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from document_loader import DocumentLoader
from rag_engine import RAGEngine

WEB_FOLDER = "./web"
UPLOAD_FOLDER = "./documents"
DB_FOLDER = "./db"
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'xlsx', 'png', 'jpg', 'jpeg', 'docx', 'pptx'}
MAX_FILE_SIZE = 500 * 1024 * 1024 
QUERY_TIMEOUT = 60 # Seconds

# Setup Rate Limiter
limiter = Limiter(key_func=get_remote_address)

if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

app = FastAPI(title="Local RAG System (Enterprise)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag_system = RAGEngine(DB_FOLDER)
system_state = {"is_db_ready": False}

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

def sanitize_input(text: str) -> str:
    """Sanitize input to prevent injection/XSS."""
    text = html.escape(text)
    for keyword in ['DROP ', 'DELETE ', 'INSERT ', 'UPDATE ']:
        text = text.replace(keyword, '')
    return text[:2000]

def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.get("/api/status")
async def check_status():
    if system_state["is_db_ready"]: return {"status": "ready"}
    if os.listdir(UPLOAD_FOLDER): return {"status": "ready", "msg": "Needs Refresh"}
    return {"status": "initializing"}

@app.get("/api/documents")
async def list_documents(page: int = 1, limit: int = 50):
    """Paginated document listing."""
    docs = []
    if os.path.exists(UPLOAD_FOLDER):
        files = sorted(os.listdir(UPLOAD_FOLDER))
        total = len(files)
        start = (page - 1) * limit
        paginated = files[start : start + limit]
        
        for filename in paginated:
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'txt'
                docs.append({"name": filename, "type": ext, "size": size})
    return {"documents": docs, "page": page, "total": total}

@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    saved_count = 0
    for file in files:
        if allowed_file(file.filename):
            file_path = os.path.normpath(os.path.join(UPLOAD_FOLDER, file.filename))
            
            # Async File Write (Non-blocking)
            try:
                async with aiofiles.open(file_path, 'wb') as out:
                    while content := await file.read(1024 * 1024):
                        await out.write(content)
            except Exception as e:
                print(f"Upload Error: {e}")
                continue

            if os.path.getsize(file_path) > MAX_FILE_SIZE:
                os.remove(file_path)
                continue
            saved_count += 1
            
    if saved_count > 0: return {"success": True, "msg": f"Uploaded {saved_count}"}
    return JSONResponse(status_code=400, content={"success": False, "msg": "Invalid files"})

@app.post("/api/refresh")
async def refresh_database():
    try:
        loader = DocumentLoader(UPLOAD_FOLDER)
        chunks_gen = loader.process_file_generator()
        # RAG update is CPU-bound; keeping it blocking here for simplicity
        # Ideally moved to background task (Celery)
        rag_system.initialize_db(chunks_generator=chunks_gen, batch_size=200)
        system_state["is_db_ready"] = True
        return {"success": True}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

@app.post("/api/query")
@limiter.limit("20/minute") # Security: Rate Limiting
async def query_rag(request: Request, body: QueryRequest):
    if not system_state["is_db_ready"]:
        return JSONResponse(status_code=400, content={"success": False, "msg": "DB not ready"})
    
    clean_query = sanitize_input(body.query)
    
    try:
        # Timeout Protection
        async def run_query():
            qa_chain = rag_system.get_qa_chain()
            payload = {"input": clean_query, "query": clean_query}
            return await asyncio.to_thread(qa_chain.invoke, payload)

        response = await asyncio.wait_for(run_query(), timeout=QUERY_TIMEOUT)
        
        answer = response.get('answer') or response.get('result')
        source_docs = response.get('context') or response.get('source_documents') or []
        rich_sources = rag_system.enrich_sources(source_docs)
                
        return {"success": True, "answer": answer, "sources": rich_sources}
        
    except asyncio.TimeoutError:
        return JSONResponse(status_code=504, content={"success": False, "msg": "Query Timeout"})
    except Exception as e:
        print(f"Query Error: {e}")
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

app.mount("/", StaticFiles(directory=WEB_FOLDER, html=True), name="static")