import os
import glob
import fitz  # PyMuPDF
import pandas as pd
from typing import Iterator
from langchain_community.document_loaders import CSVLoader, TextLoader
from langchain_core.documents import Document
from rapidocr_onnxruntime import RapidOCR
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentLoader:
    """
    Enterprise Loader (English Optimized):
    - Uses PyMuPDF for speed (10k+ pages support).
    - Uses RapidOCR for scanned docs.
    - Optimized chunking for English text structure.
    """

    def __init__(self, directory_path="./documents"):
        self.directory_path = directory_path
        
        # Initialize RapidOCR
        try:
            self.ocr_engine = RapidOCR()
        except:
            self.ocr_engine = None
            print("⚠️ Warning: RapidOCR not initialized.")

        # English-Optimized Splitter
        # Larger chunk size for English to capture full context
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1200, 
            chunk_overlap=300,
            separators=["\n\n", "\n", ". ", "! ", "? ", ";", ",", " ", ""]
        )

    def extract_text_from_scanned_page(self, page):
        """Helper: Convert PDF page to image and run OCR"""
        if not self.ocr_engine: return ""
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            img_bytes = pix.tobytes("png")
            result, _ = self.ocr_engine(img_bytes)
            if result:
                return "\n".join([line[1] for line in result])
            return ""
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""

    def process_file_generator(self) -> Iterator[Document]:
        """
        Generator for massive files.
        """
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
            return

        print(f"🔍 Scanning documents in {self.directory_path}...")

        # --- 1. PDF Files (Hybrid Strategy) ---
        pdf_files = glob.glob(os.path.join(self.directory_path, "*.pdf"))
        for file_path in pdf_files:
            doc = None
            try:
                print(f"📖 Processing PDF: {os.path.basename(file_path)}...")
                doc = fitz.open(file_path)
                
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    source_type = "digital"
                    
                    # Check for scanned pages (low text count)
                    if len(text.strip()) < 50:
                        ocr_text = self.extract_text_from_scanned_page(page)
                        if len(ocr_text.strip()) > len(text.strip()):
                            text = ocr_text
                            source_type = "scanned"
                    
                    if text.strip():
                        page_doc = Document(
                            page_content=text,
                            metadata={
                                "source": file_path,
                                "page": page_num + 1,
                                "type": source_type
                            }
                        )
                        chunks = self.text_splitter.split_documents([page_doc])
                        for chunk in chunks:
                            yield chunk
                            
            except Exception as e:
                print(f"❌ Error processing PDF {file_path}: {e}")
            finally:
                if doc: doc.close()

        # --- 2. Text Files (.txt) ---
        txt_files = glob.glob(os.path.join(self.directory_path, "*.txt"))
        for file_path in txt_files:
            try:
                print(f"📝 Processing TXT: {os.path.basename(file_path)}...")
                loader = TextLoader(file_path, encoding='utf-8')
                docs = loader.load()
                chunks = self.text_splitter.split_documents(docs)
                for chunk in chunks:
                    yield chunk
            except Exception as e:
                print(f"❌ Error loading TXT {file_path}: {e}")

        # --- 3. CSV & Excel (Data Files) ---
        # (Same efficient loading logic)
        csv_files = glob.glob(os.path.join(self.directory_path, "*.csv"))
        for file_path in csv_files:
            try:
                print(f"📊 Processing CSV: {os.path.basename(file_path)}...")
                loader = CSVLoader(file_path=file_path, encoding="utf-8")
                for doc in loader.load(): yield doc
            except Exception as e: print(f"❌ Error CSV {file_path}: {e}")

        xlsx_files = glob.glob(os.path.join(self.directory_path, "*.xlsx"))
        for file_path in xlsx_files:
            try:
                print(f"📉 Processing Excel: {os.path.basename(file_path)}...")
                df = pd.read_excel(file_path)
                for index, row in df.iterrows():
                    row_content = ", ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                    doc = Document(
                        page_content=row_content,
                        metadata={"source": file_path, "row": index, "type": "structured_data"}
                    )
                    yield doc
            except Exception as e: print(f"❌ Error Excel {file_path}: {e}")