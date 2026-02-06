import os
import glob
import fitz  # PyMuPDF
import pandas as pd
import torch
from typing import Iterator
from PIL import Image
from docx import Document as DocxDocument
from pptx import Presentation
from langchain_community.document_loaders import CSVLoader, TextLoader
from langchain_core.documents import Document
from rapidocr_onnxruntime import RapidOCR
from langchain_text_splitters import RecursiveCharacterTextSplitter

class DocumentLoader:
    """
    Enterprise Loader (English Optimized):
    - Supports: PDF, DOCX, PPTX, Images, TXT, CSV, Excel.
    - Features: Hybrid OCR (GPU/CPU), Smart Chunking, Generator Streaming.
    """

    def __init__(self, directory_path="./documents"):
        # Fix: Normalize path for cross-platform compatibility
        self.directory_path = os.path.normpath(directory_path)
        
        # 1. كشف الـ GPU للـ OCR
        use_gpu = torch.cuda.is_available()
        device_name = "GPU" if use_gpu else "CPU"
        
        try:
            self.ocr_engine = RapidOCR(det_use_gpu=use_gpu, cls_use_gpu=use_gpu, rec_use_gpu=use_gpu)
            print(f"🚀 RapidOCR initialized on: {device_name}")
        except Exception as e:
            print(f"⚠️ Warning: RapidOCR init failed on {device_name}. Error: {e}")
            try:
                self.ocr_engine = RapidOCR(det_use_gpu=False, cls_use_gpu=False, rec_use_gpu=False)
                print("⚠️ Fallback to RapidOCR on CPU success.")
            except:
                self.ocr_engine = None
                print("❌ RapidOCR completely disabled.")

        # تقسيم النص (إنجليزي محسن)
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def run_ocr_on_image(self, image_bytes):
        """Helper for OCR on bytes"""
        if not self.ocr_engine: return ""
        try:
            result, _ = self.ocr_engine(image_bytes)
            if result:
                return "\n".join([line[1] for line in result])
        except Exception as e:
            print(f"OCR Error: {e}")
        return ""

    def process_file_generator(self) -> Iterator[Document]:
        """
        Generator for massive files. Prevents RAM overflow.
        """
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
            return

        print(f"🔍 Scanning documents in {self.directory_path}...")
        
        # Get all files
        all_files = glob.glob(os.path.join(self.directory_path, "*.*"))
        
        for file_path in all_files:
            file_path = os.path.normpath(file_path)
            ext = file_path.rsplit('.', 1)[-1].lower()
            
            try:
                # === 1. PDF Handling (Smart Hybrid) ===
                if ext == 'pdf':
                    print(f"📖 Processing PDF: {os.path.basename(file_path)}")
                    doc = fitz.open(file_path)
                    for page_num, page in enumerate(doc):
                        text = page.get_text()
                        source_type = "digital"
                        
                        # Fix: Better OCR Logic (Check content density)
                        blocks = page.get_text("blocks")
                        # If text is short AND has few blocks -> likely scanned/title/image
                        if len(text.strip()) < 50 and len(blocks) < 3:
                            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                            ocr_text = self.run_ocr_on_image(pix.tobytes("png"))
                            
                            if len(ocr_text.strip()) > len(text.strip()):
                                text = ocr_text
                                source_type = "scanned"
                        
                        if text.strip():
                            yield from self._create_chunks(text, file_path, page=page_num+1, type=source_type)
                    doc.close()

                # === 2. PowerPoint Handling ===
                elif ext == 'pptx':
                    print(f"📊 Processing PowerPoint: {os.path.basename(file_path)}")
                    prs = Presentation(file_path)
                    for i, slide in enumerate(prs.slides):
                        slide_text = []
                        for shape in slide.shapes:
                            if hasattr(shape, "text") and shape.text.strip():
                                slide_text.append(shape.text)
                        full_text = "\n".join(slide_text)
                        if full_text.strip():
                            yield from self._create_chunks(full_text, file_path, page=i+1, type="slide")

                # === 3. Word Handling ===
                elif ext == 'docx':
                    print(f"📝 Processing Word: {os.path.basename(file_path)}")
                    doc = DocxDocument(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    if text.strip():
                        yield from self._create_chunks(text, file_path, type="docx")

                # === 4. Image Handling ===
                elif ext in ['png', 'jpg', 'jpeg', 'bmp']:
                    print(f"🖼️ Processing Image: {os.path.basename(file_path)}")
                    with open(file_path, "rb") as f:
                        img_bytes = f.read()
                    text = self.run_ocr_on_image(img_bytes)
                    if text.strip():
                        yield from self._create_chunks(text, file_path, type="image")

                # === 5. Text/CSV/Excel Handling ===
                elif ext == 'txt':
                    loader = TextLoader(file_path, encoding='utf-8')
                    for d in loader.load():
                        yield from self._create_chunks(d.page_content, file_path, type="text")

                elif ext == 'csv':
                    loader = CSVLoader(file_path, encoding='utf-8')
                    for d in loader.load(): yield d
                
                elif ext == 'xlsx':
                    df = pd.read_excel(file_path)
                    for idx, row in df.iterrows():
                        content = ", ".join([f"{k}:{v}" for k,v in row.items() if pd.notna(v)])
                        yield Document(page_content=content, metadata={"source": file_path, "row": idx})

            except Exception as e:
                print(f"❌ Error processing {os.path.basename(file_path)}: {e}")

    def _create_chunks(self, text, source, **kwargs):
        """Helper to split text and yield documents"""
        doc = Document(page_content=text, metadata={"source": source, **kwargs})
        chunks = self.text_splitter.split_documents([doc])
        for chunk in chunks:
            yield chunk