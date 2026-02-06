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

# ✅ FIX P0: Security Constants
ALLOWED_EXTENSIONS = {'pdf', 'txt', 'csv', 'xlsx', 'png', 'jpg', 'jpeg', 'docx', 'pptx'}
MAX_FILE_SIZE = 500 * 1024 * 1024 

limiter = Limiter(key_func=get_remote_address)
if not os.path.exists(UPLOAD_FOLDER): os.makedirs(UPLOAD_FOLDER)

app = FastAPI(title="Local RAG System (Enterprise)")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

rag_system = RAGEngine(DB_FOLDER)
auditor = TraceabilityAuditor()
system_state = {"is_db_ready": False}

if os.path.exists(DB_FOLDER) and os.listdir(DB_FOLDER):
    try: rag_system.initialize_db(); system_state["is_db_ready"] = True
    except: pass

class QueryRequest(BaseModel):
    query: str

# Helper for file validation
def validate_file(filename: str, size: int):
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed.")
    if size > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large.")

@app.post("/api/traceability/master-upload")
@limiter.limit("5/minute") # ✅ Rate Limit Added
async def upload_master_list(request: Request, file: UploadFile = File(...)):
    try:
        content = await file.read()
        validate_file(file.filename, len(content)) # Check size
        
        decoded = content.decode('utf-8')
        csv_reader = csv.reader(io.StringIO(decoded))
        next(csv_reader, None)
        reqs = [(row[0].strip(), row[1].strip(), row[2].strip() if len(row)>2 else "Gen", "Active") for row in csv_reader if len(row)>=2]
        
        rag_system.metadata_store.add_master_requirements(reqs)
        # ✅ Audit Log
        rag_system.metadata_store.log_action("MASTER_UPLOAD", file.filename, "SUCCESS", f"Added {len(reqs)} reqs")
        return {"success": True, "count": len(reqs)}
    except Exception as e:
        rag_system.metadata_store.log_action("MASTER_UPLOAD", file.filename, "FAILED", str(e))
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

@app.get("/api/traceability/audit-report")
async def get_audit_report(page: int = 1, limit: int = 50):
    return auditor.generate_gap_report(page=page, page_size=limit)

@app.post("/api/upload")
@limiter.limit("10/minute") # ✅ Rate Limit Added
async def upload_files(request: Request, files: List[UploadFile] = File(...)):
    saved = 0
    errors = []
    for file in files:
        try:
            # Check content length immediately if available, otherwise check after read
            file_path = os.path.normpath(os.path.join(UPLOAD_FOLDER, file.filename))
            
            # Streaming write with size check
            size = 0
            async with aiofiles.open(file_path, 'wb') as out:
                while content := await file.read(1024*1024):
                    size += len(content)
                    if size > MAX_FILE_SIZE:
                        out.close()
                        os.remove(file_path)
                        raise HTTPException(400, "File exceeded max size during upload")
                    await out.write(content)
            
            validate_file(file.filename, size) # Final check
            saved += 1
            rag_system.metadata_store.log_action("FILE_UPLOAD", file.filename, "SUCCESS")
        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
            rag_system.metadata_store.log_action("FILE_UPLOAD", file.filename, "FAILED", str(e))
            
    return {"success": True, "msg": f"Uploaded {saved}, Errors: {len(errors)}"}

@app.post("/api/refresh")
@limiter.limit("2/minute") # ✅ Strict Limit for heavy task
async def refresh_database(request: Request):
    try:
        rag_system.metadata_store.log_action("REFRESH", "DB", "STARTED")
        loader = DocumentLoader(UPLOAD_FOLDER)
        chunks_gen = loader.process_file_generator()
        rag_system.initialize_db(chunks_generator=chunks_gen, batch_size=200)
        system_state["is_db_ready"] = True
        rag_system.metadata_store.log_action("REFRESH", "DB", "SUCCESS")
        return {"success": True}
    except Exception as e:
        rag_system.metadata_store.log_action("REFRESH", "DB", "FAILED", str(e))
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

@app.post("/api/query")
@limiter.limit("20/minute") 
async def query_rag(request: Request, body: QueryRequest):
    if not system_state["is_db_ready"]: return JSONResponse(status_code=400, content={"success": False, "msg": "DB not ready"})
    
    clean_query = html.escape(body.query)
    try:
        async def run():
            qa = rag_system.get_qa_chain()
            return await asyncio.to_thread(qa.invoke, {"input": clean_query, "query": clean_query})
        
        resp = await asyncio.wait_for(run(), timeout=QUERY_TIMEOUT)
        ans = resp.get('answer') or resp.get('result')
        srcs = rag_system.enrich_sources(resp.get('context') or resp.get('source_documents') or [])
        
        # ✅ Audit Log Query
        rag_system.metadata_store.log_action("QUERY", clean_query[:50], "SUCCESS")
        return {"success": True, "answer": ans, "sources": srcs}
    except Exception as e:
        rag_system.metadata_store.log_action("QUERY", clean_query[:50], "FAILED", str(e))
        return JSONResponse(status_code=500, content={"success": False, "msg": str(e)})

app.mount("/", StaticFiles(directory=WEB_FOLDER, html=True), name="static")