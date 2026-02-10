import os
import asyncio
import aiofiles
import html
import csv
import io
from typing import List
from fastapi import FastAPI, File, UploadFile, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from document_loader import DocumentLoader
from rag_engine import RAGEngine
from traceability_auditor import TraceabilityAuditor

WEB_FOLDER = "./web"
UPLOAD_FOLDER = "./documents"
DB_FOLDER = "./db"
QUERY_TIMEOUT = 60

# Security Constants
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'xlsx', 'png', 'jpg', 'jpeg', 'docx', 'pptx'}
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500 MB

limiter = Limiter(key_func=get_remote_address)
if not os.path.exists(UPLOAD_FOLDER): 
    os.makedirs(UPLOAD_FOLDER)

app = FastAPI(title="Local RAG System (Enterprise)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

rag_system = RAGEngine(DB_FOLDER)
auditor = TraceabilityAuditor()
system_state = {"is_db_ready": False}

# Initialize DB if exists
if os.path.exists(DB_FOLDER) and os.listdir(DB_FOLDER):
    try: 
        rag_system.initialize_db()
        system_state["is_db_ready"] = True
        print("✅ Vector database loaded successfully")
    except Exception as e:
        print(f"⚠️ Database initialization failed: {e}")

class QueryRequest(BaseModel):
    query: str

def validate_file(filename: str, size: int):
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}")
    if size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE / (1024*1024)} MB")

@app.get("/api/status")
async def get_status():
    """Returns system status for frontend monitoring"""
    return {
        "status": "ready" if system_state["is_db_ready"] else "initializing",
        "message": "System Ready" if system_state["is_db_ready"] else "Database initializing...",
        "db_ready": system_state["is_db_ready"]
    }

@app.get("/api/documents")
async def get_documents():
    """Returns list of uploaded documents with statistics"""
    try:
        documents = []
        stats = {"chunks": 0, "embeddings": 0}
        
        if os.path.exists(UPLOAD_FOLDER):
            for filename in os.listdir(UPLOAD_FOLDER):
                # ✅ FIXED: 'filenam e' → 'filename' (critical variable name corruption)
                file_path = os.path.join(UPLOAD_FOLDER, filename)
                if os.path.isfile(file_path):
                    file_size = os.path.getsize(file_path)
                    # ✅ FIXED: 'el se' → 'else' (critical keyword corruption)
                    file_ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                    
                    documents.append({
                        "id": filename,
                        "name": filename,
                        "type": file_ext,
                        "size": file_size
                    })
        
        if system_state["is_db_ready"] and rag_system.vector_db:
            try:
                collection = rag_system.vector_db._collection
                count = collection.count()
                stats["chunks"] = count
                stats["embeddings"] = count
            except Exception as e:
                print(f"Vector DB stats error: {e}")
        
        return {
            "success": True,
            "documents": documents,
            "stats": stats
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500, 
            content={"success": False, "message": str(e), "documents": [], "stats": {"chunks": 0, "embeddings": 0}}
        )

@app.post("/api/traceability/master-upload")
@limiter.limit("5/minute")
async def upload_master_list(request: Request, file: UploadFile = File(...)):
    try:
        content = await file.read()
        validate_file(file.filename, len(content))
        
        decoded = content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(decoded))
        next(csv_reader, None)  # Skip header
        
        # ✅ FIXED: 'le n(row)' → 'len(row)' (critical function name corruption)
        reqs = [
            (row[0].strip(), row[1].strip(), row[2].strip() if len(row) > 2 else "General", "Active")
            for row in csv_reader if len(row) >= 2
        ]
        
        rag_system.metadata_store.add_master_requirements(reqs)
        rag_system.metadata_store.log_action("MASTER_UPLOAD", file.filename, "SUCCESS", f"Added {len(reqs)} requirements")
        return {"success": True, "count": len(reqs)}
    except Exception as e:
        rag_system.metadata_store.log_action("MASTER_UPLOAD", file.filename, "FAILED", str(e))
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

@app.get("/api/traceability/audit-report")
async def get_audit_report(page: int = 1, limit: int = 50):
    try:
        report = auditor.generate_gap_report(page=page, page_size=limit)
        rag_system.metadata_store.log_action("AUDIT_REPORT", f"page={page}", "SUCCESS")
        return report
    except Exception as e:
        rag_system.metadata_store.log_action("AUDIT_REPORT", f"page={page}", "FAILED", str(e))
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

@app.post("/api/upload")
@limiter.limit("10/minute")
async def upload_files(request: Request, files: List[UploadFile] = File(...)):
    saved = 0
    errors = []
    for file in files:
        try:
            file_path = os.path.normpath(os.path.join(UPLOAD_FOLDER, file.filename))
            size = 0
            async with aiofiles.open(file_path, 'wb') as out:
                while content := await file.read(1024*1024):
                    size += len(content)
                    if size > MAX_FILE_SIZE:
                        await out.close()
                        os.remove(file_path)
                        raise HTTPException(400, "File exceeded max size during upload")
                    await out.write(content)
            
            validate_file(file.filename, size)
            saved += 1
            rag_system.metadata_store.log_action("FILE_UPLOAD", file.filename, "SUCCESS")
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            rag_system.metadata_store.log_action("FILE_UPLOAD", file.filename, "FAILED", str(e))
    
    return {"success": True, "msg": f"Uploaded {saved}, Errors: {len(errors)}", "errors": errors}

@app.post("/api/refresh")
@limiter.limit("2/minute")
async def refresh_database(request: Request):
    try:
        rag_system.metadata_store.log_action("REFRESH", "DB", "STARTED")
        loader = DocumentLoader(UPLOAD_FOLDER)
        chunks_gen = loader.process_file_generator()
        rag_system.initialize_db(chunks_generator=chunks_gen, batch_size=200)
        system_state["is_db_ready"] = True
        rag_system.metadata_store.log_action("REFRESH", "DB", "SUCCESS")
        return {"success": True, "message": "Database refreshed successfully"}
    except Exception as e:
        rag_system.metadata_store.log_action("REFRESH", "DB", "FAILED", str(e))
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

@app.post("/api/query")
@limiter.limit("20/minute")
async def query_rag(request: Request, body: QueryRequest):
    if not system_state["is_db_ready"]:
        return JSONResponse(status_code=400, content={"success": False, "msg": "Database not ready. Upload documents and refresh first."})
    
    clean_query = html.escape(body.query[:500])  # Sanitize and limit length
    
    try:
        async def run():
            qa = rag_system.get_qa_chain()
            return await asyncio.to_thread(qa.invoke, {"query": clean_query})
        
        resp = await asyncio.wait_for(run(), timeout=QUERY_TIMEOUT)
        # ✅ FIXED: 'resp.g et' → 'resp.get' (critical method name corruption)
        ans = resp.get('answer') or resp.get('result', '')
        srcs = rag_system.enrich_sources(resp.get('source_documents', []))
        
        rag_system.metadata_store.log_action("QUERY", clean_query[:50], "SUCCESS")
        return {"success": True, "answer": ans, "sources": srcs}
    except asyncio.TimeoutError:
        rag_system.metadata_store.log_action("QUERY", clean_query[:50], "FAILED", "Timeout")
        return JSONResponse(status_code=504, content={"success": False, "msg": "Query timed out after 60 seconds"})
    except Exception as e:
        rag_system.metadata_store.log_action("QUERY", clean_query[:50], "FAILED", str(e))
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"success": False, "msg": f"Query failed: {str(e)}"})

# Serve static files last to avoid route conflicts
if os.path.exists(WEB_FOLDER):
    app.mount("/", StaticFiles(directory=WEB_FOLDER, html=True), name="static")
else:
    print("⚠️ WARNING: 'web' folder not found. UI will not be available.")