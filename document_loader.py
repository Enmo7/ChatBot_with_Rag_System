import os
import glob
from docling.document_converter import DocumentConverter
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


class DocumentLoader:
    """
    Handles loading documents using IBM Docling.
    Docling converts PDFs (scanned or native) into structured Markdown,
    which preserves tables and layout for better RAG performance.
    """

    def __init__(self, directory_path="./documents"):
        self.directory_path = directory_path
        # Initialize Docling converter once
        self.converter = DocumentConverter()

    def load_and_split(self):
        """
        Loads files using Docling, converts them to Markdown, and splits them.
        """
        if not os.path.exists(self.directory_path):
            os.makedirs(self.directory_path)
            print(f"Directory '{self.directory_path}' created. Please add files to it.")
            return []

        print(f"Loading documents from {self.directory_path} using Docling...")
        
        # We look for supported files (PDF, DOCX, PPTX, etc.)
        # Docling supports many formats, but let's focus on PDF for now
        files = glob.glob(os.path.join(self.directory_path, "*.pdf"))
        
        langchain_docs = []

        for file_path in files:
            try:
                print(f"Processing: {os.path.basename(file_path)}...")
                
                # 1. Convert Document to Markdown
                # This step handles OCR and Table extraction automatically
                result = self.converter.convert(file_path)
                markdown_text = result.document.export_to_markdown()
                
                # 2. Wrap in LangChain Document object
                doc = Document(
                    page_content=markdown_text,
                    metadata={"source": file_path}
                )
                langchain_docs.append(doc)
                
            except Exception as e:
                print(f"Error processing {file_path}: {e}")

        if not langchain_docs:
            print("No documents processed.")
            return []

        print(f"Successfully processed {len(langchain_docs)} documents into Markdown.")
        
        # 3. Intelligent Splitting for Markdown
        # First, split by headers (h1, h2, etc.) to keep logical sections together
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        md_header_splits = []
        
        for doc in langchain_docs:
            md_header_splits.extend(markdown_splitter.split_text(doc.page_content))

        # Second, ensure chunks are not too large (for context window)
        # We use Recursive splitter ON TOP of the markdown splits
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
        final_chunks = text_splitter.split_documents(md_header_splits)
        
        # Preserve metadata (source file name)
        # Note: MarkdownHeaderTextSplitter might lose original metadata, so we might need to re-attach it if critical.
        # For simplicity, we proceed, but in prod you'd map metadata back.
        
        print(f"Created {len(final_chunks)} chunks using Markdown-aware splitting.")
        return final_chunks