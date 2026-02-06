import os
import glob
import fitz  # PyMuPDF
import re
import gc
import psutil
import tempfile
import time
from typing import Iterator
from PIL import Image
from docx import Document as DocxDocument
from pptx import Presentation
from langchain_community.document_loaders import TextLoader
from langchain_core.documents import Document
from rapidocr_onnxruntime import RapidOCR
from langchain_text_splitters import RecursiveCharacterTextSplitter
from metadata_store import MetadataStore

class DocumentLoader:
    """
    Enterprise Loader with Optimization & Safety:
    - Dynamic Batch Processing for PDFs.
    - Memory Monitoring & Safety Pauses.
    - TempFile usage for large images (Zero RAM spike).
    - Advanced Traceability Context Analysis.
    """

    def __init__(self, directory_path="./documents"):
        self.directory_path = os.path.normpath(directory_path)
        self.metadata_store = MetadataStore()
        
        # GPU Check
        import torch
        use_gpu = torch.cuda.is_available()
        try:
            self.ocr_engine = RapidOCR(det_use_gpu=use_gpu, cls_use_gpu=use_gpu, rec_use_gpu=use_gpu)
            print(f"🚀 RapidOCR initialized on: {'GPU' if use_gpu else 'CPU'}")
        except:
            self.ocr_engine = None

        # Increased chunk size to reduce total vectors
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000, 
            chunk_overlap=300,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Regex for Requirement IDs
        self.link_pattern = re.compile(r'\b(REQ|TC|SRS|TEST|BUG)-?\d+\b', re.IGNORECASE)

    # --- SAFETY & MONITORING ---
    def check_memory(self):
        """Monitors RAM. Forces GC if usage is > 90%."""
        if psutil.virtual_memory().percent > 90:
            print("⚠️ High Memory detected! Pausing for GC...")
            gc.collect()
            time.sleep(2)
            return False
        return True

    def get_optimal_batch_size(self, file_path):
        """Calculates batch size based on file size."""
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > 1000: return 10 # > 1GB
            if size_mb > 500: return 20  # > 500MB
            return 50 # Standard
        except: return 50

    # --- ADVANCED TRACEABILITY ---
    def analyze_link_context(self, text, link):
        """Checks if the link has meaningful context around it (Quality Check)."""
        try:
            idx = text.find(link)
            if idx == -1: return False
            
            # Get 50 chars context
            start = max(0, idx - 50)
            end = min(len(text), idx + len(link) + 50)
            context = text[start:end]
            
            # Valid if context has > 5 words
            return len(context.split()) > 5
        except:
            return False

    def extract_links_with_quality(self, text):
        """Extracts links and filters based on context quality."""
        if not text: return []
        raw_links = list(set(self.link_pattern.findall(text)))
        
        valid_links = []
        for link in raw_links:
            if self.analyze_link_context(text, link):
                valid_links.append(link)
        
        return valid_links

    # --- OPTIMIZED OCR ---
    def run_ocr_safely(self, image_source):
        """Runs OCR using TempFile to avoid RAM spikes on large images."""
        if not self.ocr_engine: return ""
        
        temp_file = None
        try:
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_file.close() # Close so other processes can read it
            
            # Write to disk
            if isinstance(image_source, bytes):
                with open(temp_file.name, 'wb') as f: f.write(image_source)
            else: # PIL Image
                image_source.save(temp_file.name)
            
            # Read safely
            with open(temp_file.name, 'rb') as f:
                img_bytes = f.read()
                
            result, _ = self.ocr_engine(img_bytes)
            return "\n".join([line[1] for line in result]) if result else ""
            
        except Exception as e:
            print(f"OCR Error: {e}")
            return ""
        finally:
            if temp_file and os.path.exists(temp_file.name):
                os.unlink(temp_file.name)

    # --- PROCESSORS ---
    def process_pdf_in_batches(self, file_path, file_hash) -> Iterator[Document]:
        batch_size = self.get_optimal_batch_size(file_path)
        doc = fitz.open(file_path)
        total_pages = len(doc)
        start_time = time.time()
        
        print(f"   ↳ Processing '{os.path.basename(file_path)}' ({total_pages} pages)")
        
        try:
            for batch_start in range(0, total_pages, batch_size):
                if not self.check_memory(): pass

                batch_end = min(batch_start + batch_size, total_pages)
                
                # Progress / ETA
                elapsed = time.time() - start_time
                pages_done = batch_start
                if pages_done > 0:
                    rate = pages_done / elapsed # pages/sec
                    remaining = (total_pages - pages_done) / rate
                    print(f"   📊 Batch {batch_start}-{batch_end} | Speed: {rate:.1f} p/s | ETA: {remaining/60:.1f} min")

                for i in range(batch_start, batch_end):
                    try:
                        page = doc.load_page(i)
                        text = page.get_text()
                        source_type = "digital"
                        
                        # Memory-Safe OCR Trigger
                        if len(text.strip()) < 50:
                            # 1. Low Res Check (Fast & Low RAM)
                            pix_check = page.get_pixmap(matrix=fitz.Matrix(1.0, 1.0))
                            if pix_check.size < 5 * 1024 * 1024: # Only check if < 5MB
                                # 2. Run Safe OCR via TempFile
                                ocr_text = self.run_ocr_safely(pix_check.tobytes("png"))
                                if len(ocr_text.strip()) > len(text.strip()):
                                    text = ocr_text
                                    source_type = "scanned"
                            pix_check = None

                        if text.strip():
                            links = self.extract_links_with_quality(text)
                            yield from self._create_chunks(
                                text, file_path, file_hash=file_hash, 
                                page=i+1, type=source_type, 
                                found_links=",".join(links)
                            )
                        page = None # Dereference
                    except Exception as e:
                        print(f"   ⚠️ Page {i} Error: {e}")

                gc.collect() # Clean batch memory
        finally:
            doc.close()

    def process_image_safely(self, file_path, file_hash) -> Iterator[Document]:
        """Processes images using safe OCR method."""
        try:
            with Image.open(file_path) as img:
                # Resize if massive (4k+)
                if img.width > 4000 or img.height > 4000:
                    img.thumbnail((4000, 4000))
                text = self.run_ocr_safely(img)
                
            if text.strip():
                links = self.extract_links_with_quality(text)
                yield from self._create_chunks(text, file_path, file_hash=file_hash, type="image", found_links=",".join(links))
        except Exception as e:
            print(f"   ❌ Image Error: {e}")

    # --- MAIN GENERATOR ---
    def process_file_generator(self) -> Iterator[Document]:
        if not os.path.exists(self.directory_path): return
        
        all_files = glob.glob(os.path.join(self.directory_path, "*.*"))
        for file_path in all_files:
            try:
                # Register in Traceability DB
                file_hash, is_new = self.metadata_store.register_document(file_path, os.path.basename(file_path))
                if not file_hash: continue
                
                ext = file_path.rsplit('.', 1)[-1].lower()
                
                # Routing based on file type
                if ext == 'pdf':
                    yield from self.process_pdf_in_batches(file_path, file_hash)
                
                elif ext in ['png', 'jpg', 'jpeg', 'bmp']:
                    yield from self.process_image_safely(file_path, file_hash)
                
                elif ext == 'docx':
                    doc = DocxDocument(file_path)
                    text = "\n".join([para.text for para in doc.paragraphs])
                    if text.strip():
                        links = self.extract_links_with_quality(text)
                        yield from self._create_chunks(text, file_path, file_hash=file_hash, type="docx", found_links=",".join(links))
                
                elif ext == 'pptx':
                    prs = Presentation(file_path)
                    for i, slide in enumerate(prs.slides):
                        full_text = "\n".join([shape.text for shape in slide.shapes if hasattr(shape, "text")])
                        if full_text.strip():
                            links = self.extract_links_with_quality(full_text)
                            yield from self._create_chunks(full_text, file_path, file_hash=file_hash, page=i+1, type="slide", found_links=",".join(links))
                
                elif ext == 'txt':
                    loader = TextLoader(file_path, encoding='utf-8')
                    for d in loader.load():
                        links = self.extract_links_with_quality(d.page_content)
                        yield from self._create_chunks(d.page_content, file_path, file_hash=file_hash, type="text", found_links=",".join(links))

            except Exception as e:
                print(f"❌ Critical File Error: {e}")
                continue # Skip bad file

    def _create_chunks(self, text, source, **kwargs):
        doc = Document(page_content=text, metadata={"source": source, **kwargs})
        chunks = self.text_splitter.split_documents([doc])
        for chunk in chunks: yield chunk