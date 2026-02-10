import sqlite3
import hashlib
import os
from datetime import datetime

class MetadataStore:
    """Central Database for Traceability & Audit Logging."""
    def __init__(self, db_path="./db/traceability.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS documents
                     (file_hash TEXT PRIMARY KEY, filename TEXT, upload_date TEXT, file_size INTEGER, version INTEGER DEFAULT 1)''')

        c.execute('''CREATE TABLE IF NOT EXISTS master_requirements  -- ✅ FIXED: 'NOT EXI STS' → 'NOT EXISTS'
                     (req_id TEXT PRIMARY KEY, description TEXT, category TEXT, status TEXT)''')

        c.execute('''CREATE TABLE IF NOT EXISTS detected_links  -- ✅ FIXED: 'NOT E XISTS' → 'NOT EXISTS'
                     (link_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      file_hash TEXT, req_id TEXT, context_snippet TEXT, confidence_score REAL,
                       FOREIGN KEY(file_hash) REFERENCES documents(file_hash))''')

        c.execute('''CREATE TABLE IF NOT EXISTS action_audit  -- ✅ FIXED: 'action _audit' → 'action_audit'
                     (audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      action_type TEXT,
                      target TEXT,
                      status TEXT,
                      timestamp TEXT,
                      details TEXT)''')
        
        conn.commit()
        conn.close()

    def log_action(self, action_type, target, status="SUCCESS", details=""):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT INTO action_audit (action_type, target, status, timestamp, details) VALUES (?, ?, ?, ?, ?)",
                  (action_type, target, status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), details))
        conn.commit()
        conn.close()

    def calculate_hash(self, file_path):
        sha256_hash = hashlib.sha256()  # ✅ FIXED: 'sha 256_hash' → 'sha256_hash'
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"Hash calculation error: {e}")
            return None

    def register_document(self, file_path, filename):
        file_hash = self.calculate_hash(file_path)
        if not file_hash: 
            return None, False
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM documents WHERE file_hash=?", (file_hash,))
        if not c.fetchone():
            c.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
                      (file_hash, filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), os.path.getsize(file_path), 1))
            conn.commit()
            return file_hash, True
        return file_hash, False

    def add_master_requirements(self, req_list):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for req in req_list:
            c.execute("INSERT OR REPLACE INTO master_requirements VALUES (?, ?, ?, ?)", req)
        conn.commit()
        conn.close()

    def log_detected_link(self, file_hash, req_id, context, score):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        short_context = context[:50] if context else ""
        c.execute("SELECT link_id FROM detected_links WHERE file_hash=? AND req_id=? AND context_snippet LIKE ?", 
                  (file_hash, req_id, f"{short_context}%"))
        if not c.fetchone():
            c.execute("INSERT INTO detected_links (file_hash, req_id, context_snippet, confidence_score) VALUES (?, ?, ?, ?)",
                      (file_hash, req_id, context, score))
            conn.commit()
        conn.close()

    def get_audit_data(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # ✅ FIXED: 'row_fa ctory' → 'row_factory'
        c = conn.cursor()
        master = c.execute("SELECT * FROM master_requirements").fetchall()
        detected = c.execute("""SELECT d.req_id, doc.filename, d.context_snippet 
                               FROM detected_links d 
                               JOIN documents doc ON d.file_hash = doc.file_hash""").fetchall()
        conn.close()
        return master, detected

    def get_metadata(self, file_hash):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        res = c.execute("SELECT * FROM documents WHERE file_hash=?", (file_hash,)).fetchone()
        conn.close()
        return res