import sqlite3
import hashlib
import os
from datetime import datetime

class MetadataStore:
    """
    Manages Traceability Data (Who, When, What Version).
    Uses SQLite to store metadata and relationship links.
    """
    def __init__(self, db_path="./db/traceability.db"):
        self.db_path = db_path
        # Ensure the directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initializes the SQLite database schema."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Document Registry Table
        # file_hash: Unique SHA-256 fingerprint of the file content
        c.execute('''CREATE TABLE IF NOT EXISTS documents
                     (file_hash TEXT PRIMARY KEY, 
                      filename TEXT, 
                      upload_date TEXT, 
                      file_size INTEGER,
                      version INTEGER DEFAULT 1)''')
        
        conn.commit()
        conn.close()

    def calculate_hash(self, file_path):
        """Generates SHA-256 Hash streaming the file (Memory Safe)."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                # Read in 4KB chunks to avoid RAM overflow
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except FileNotFoundError:
            return None

    def register_document(self, file_path, filename):
        """
        Registers a document. Handles versioning logic.
        Returns: (file_hash, is_new)
        """
        file_hash = self.calculate_hash(file_path)
        if not file_hash:
            return None, False

        file_size = os.path.getsize(file_path)
        upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        # Check if this exact content already exists
        c.execute("SELECT * FROM documents WHERE file_hash=?", (file_hash,))
        exists = c.fetchone()
        
        is_new = False
        if not exists:
            # Check if a file with the same name exists (to increment version)
            c.execute("SELECT MAX(version) FROM documents WHERE filename=?", (filename,))
            result = c.fetchone()
            current_ver = result[0] if result and result[0] else 0
            new_version = current_ver + 1
            
            c.execute("INSERT INTO documents VALUES (?, ?, ?, ?, ?)",
                      (file_hash, filename, upload_date, file_size, new_version))
            conn.commit()
            is_new = True
            
        conn.close()
        return file_hash, is_new

    def get_metadata(self, file_hash):
        """Retrieve metadata by hash."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT * FROM documents WHERE file_hash=?", (file_hash,))
        data = c.fetchone()
        conn.close()
        return data # Returns (hash, filename, date, size, version)