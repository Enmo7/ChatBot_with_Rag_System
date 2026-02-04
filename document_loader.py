import os
import glob
import pandas as pd
from langchain_community.document_loaders import CSVLoader
from langchain_core.documents import Document
from docling.document_converter import DocumentConverter
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

class DocumentLoader:
    """
    Advanced Loader: Handles PDFs, Images, CSVs, and Excel files.
    """

    def __init__(self, directory_path="./documents"):
        self.directory_path = directory_path
        # Docling converter (for PDFs and Images)
        self.converter = DocumentConverter()

    def load_and_split(self):
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
            print(f"Directory '{self.directory_path}' created. Please add files.")
            return []

        print(f"🔍 Scanning documents in {self.directory_path}...")
        
        all_docs = []

        # --- 1. Images & PDFs (Using Docling with OCR) ---
        # Docling supports: pdf, png, jpg, jpeg, docx, pptx
        docling_extensions = ["*.pdf", "*.png", "*.jpg", "*.jpeg", "*.docx"]
        docling_files = []
        for ext in docling_extensions:
            docling_files.extend(glob.glob(os.path.join(self.directory_path, ext)))

        for file_path in docling_files:
            try:
                print(f"📄 Processing (Docling): {os.path.basename(file_path)}...")
                result = self.converter.convert(file_path)
                markdown_text = result.document.export_to_markdown()
                
                doc = Document(
                    page_content=markdown_text,
                    metadata={"source": file_path, "type": "unstructured"}
                )
                all_docs.append(doc)
            except Exception as e:
                print(f"❌ Error loading {file_path}: {e}")

        # --- 2. CSV Files (Using LangChain CSVLoader) ---
        csv_files = glob.glob(os.path.join(self.directory_path, "*.csv"))
        for file_path in csv_files:
            try:
                print(f"📊 Processing (CSV): {os.path.basename(file_path)}...")
                loader = CSVLoader(file_path=file_path, encoding="utf-8")
                # CSVLoader creates one document per ROW automatically
                all_docs.extend(loader.load())
            except Exception as e:
                print(f"❌ Error loading CSV {file_path}: {e}")

        # --- 3. Excel Files (Using Pandas for custom formatting) ---
        xlsx_files = glob.glob(os.path.join(self.directory_path, "*.xlsx"))
        for file_path in xlsx_files:
            try:
                print(f"📉 Processing (Excel): {os.path.basename(file_path)}...")
                # Read Excel
                df = pd.read_excel(file_path)
                # Convert each row to a text string: "Column: Value, Column: Value"
                # This helps the LLM understand the context of the data
                for index, row in df.iterrows():
                    row_content = ", ".join([f"{col}: {val}" for col, val in row.items() if pd.notna(val)])
                    doc = Document(
                        page_content=row_content,
                        metadata={"source": file_path, "row": index, "type": "structured_data"}
                    )
                    all_docs.append(doc)
            except Exception as e:
                print(f"❌ Error loading Excel {file_path}: {e}")

        if not all_docs:
            print("⚠️ No documents processed.")
            return []

        print(f"✅ Loaded {len(all_docs)} raw documents/rows.")

        # --- Splitting Strategy ---
        final_chunks = []
        
        # Splitter for general text (Images/PDFs)
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

        for doc in all_docs:
            # If it's a CSV or Excel row, it's usually small enough, so we don't split it further
            # unless it's huge.
            if doc.metadata.get("type") == "structured_data" or len(doc.page_content) < 1000:
                final_chunks.append(doc)
            else:
                # If it's a long PDF/Image text, split it
                splits = text_splitter.split_documents([doc])
                final_chunks.extend(splits)

        print(f"📦 Final database chunks created: {len(final_chunks)}")
        return final_chunks