from PyPDF2 import PdfReader
import hashlib
import logging
import uuid
from typing import List, Tuple, Dict
from django.core.files.uploadedfile import UploadedFile

bytes_chunk_size = 4096 # 4KB will be read at a time while calculating hash

def calculate_hash(file: UploadedFile) -> str:
    """
    Calculate MD5 hash of an UploadedFile
    
    Args:
        file: The uploaded file object
        
    Returns:
        MD5 hash as hexadecimal string
    """
    # this method reads the file in chunks to handle large files
    # (if we read the file as a whole, it might cause memory issues)
    
    hash_md5 = hashlib.md5()
    
    # Django UploadedFile objects have a chunks() method
    for chunk in file.chunks():
        hash_md5.update(chunk)
    
    return hash_md5.hexdigest()

def extract_text_from_pdf(pdf_path: str) -> Tuple[str, int]:
    """
    Extract all text from a PDF file
    
    Args:
        pdf_path: Path to the PDF file
        
    Returns:
        Tuple of (extracted_text, page_count)
    """
    reader = PdfReader(pdf_path)
    full_text = ""
    
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
    
    return full_text, len(reader.pages)

def chunk_text_by_page(pdf_path: str, document_id: str) -> Tuple[List[str], List[Dict], List[str]]:
    """
    Extract and chunk PDF text by page
    
    Args:
        pdf_path: Path to the PDF file
        document_id: UUID of the document in database
        
    Returns:
        Tuple of (chunks, metadatas, ids)
    """
    reader = PdfReader(pdf_path)
    chunks = []
    metadatas = []
    ids = []
    
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        
        if text and text.strip():
            chunks.append(text)
            metadatas.append({
                "document_id": document_id,
                "source": pdf_path,
                "page": i + 1,
                "chunk_type": "page"
            })
            ids.append(str(uuid.uuid4()))
    
    return chunks, metadatas, ids


def chunk_text_by_size(pdf_path: str, document_id: str, chunk_size: int = 1000, overlap: int = 200) -> Tuple[List[str], List[Dict], List[str]]:
    """
    Chunk text by character count with overlap
    
    Args:
        pdf_path: Path to the PDF file
        chunk_size: Size of each chunk in characters
        overlap: Number of characters to overlap between chunks
        
    Returns:
        List of text chunks
    """
    reader = PdfReader(pdf_path)
    chunks = []
    metadatas = []
    ids = []
    
    for page_num, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text or not text.strip():
            continue
        start = 0
        chunk_index = 0
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            metadatas.append({
                "document_id": document_id,
                "source": pdf_path,
                "page": page_num + 1,
                "chunk_type": "size",
                "chunk_index": chunk_index
            })
            ids.append(str(uuid.uuid4()))
            start += (chunk_size - overlap)
            chunk_index += 1
    return chunks, metadatas, ids