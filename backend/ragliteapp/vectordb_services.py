# Chromadb services for vector storage and retrieval
import chromadb
from django.conf import settings
from typing import List, Dict, Tuple, Optional
import os
from chromadb.config import Settings
import logging

# logger
logger = logging.getLogger(__name__)

class ChromaDBService:
    def __init__(self):
        """ Initialize the ChromaDB client """
        # Chromdb_path
        chromadb_path = getattr(settings, 'CHROMA_DB_PATH', './chromadb_data')

        # ensure directory exists
        os.makedirs(chromadb_path, exist_ok=True)

        # initialize chromadb persistent client
        self.client = chromadb.PersistentClient(path=chromadb_path)

        #collection names
        self.DOCUMENT_COLLECTION_NAME = 'documents'
        self.QUERY_COLLECTION_NAME = 'cached_queries'

    def get_or_create_documents_collection(self):
        """ Get or create document collection """
        return self.client.get_or_create_collection(
            name=self.DOCUMENT_COLLECTION_NAME,
            metadata={"description": "document chunks for RAG"}
        )
    
    def get_or_create_queries_collection(self):
        """ Get or create query collection """
        return self.client.get_or_create_collection(
            name=self.QUERY_COLLECTION_NAME,
            metadata={"description": "cached query for similarity search for RAG"}
        )
    
    # add document chunks to the collection
    def add_document_chunks(
        self,
        chunks: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> int:
        """ 
        Add document chunks to the collection 

        Args:
            chunks (List[str]): List of document chunks
            metadatas (List[Dict]): List of metadata for each chunk
            ids (List[str]): List of ids for each chunk

        Returns:
            int: Number of chunks added
        """
        collection = self.get_or_create_documents_collection()
        collection.add(
            documents=chunks,
            metadatas=metadatas,
            ids=ids
        )
        return len(chunks)
    
    # search for relevant document chunks
    def search_document_chunks(
        self,
        query:str,
        k:int=3,
        document_id:Optional[str]=None
    ) -> Dict:
        """ 
        Search for relevant document chunks 

        Args:
            query (str): Query to search for
            k (int, optional): Number of results to return. Defaults to 3.
            document_id (Optional[str], optional): Document id to search for. Defaults to None.

        Returns:
            Dict: Search results
        """
        collection = self.get_or_create_documents_collection()
        where_clause = {"document_id": document_id} if document_id else None
        results = collection.query(
            query_texts=[query],
            n_results=k,
            where=where_clause
        )
        return results
    
    # delete document chunks
    def delete_document_chunks(self, document_id: str) -> int:
        """ 
        Delete document chunks 

        Args:
            document_id (str): Document id to delete chunks for

        Returns:
            int: Number of chunks deleted
        """
        collection = self.get_or_create_documents_collection()
        existing = collection.get(ids=[document_id])
        if existing['ids']:
            collection.delete(ids=[document_id])
            return len(existing['ids'])
        return 0
    
    # checking if document exists
    def check_document_exists(self, document_id: str) -> bool:
        """ 
        Check if document exists 

        Args:
            document_id (str): Document id to check for

        Returns:
            bool: True if document exists, False otherwise
        """
        collection = self.get_or_create_documents_collection()
        existing = collection.get(ids=[document_id])
        return len(existing['ids']) > 0
    
    # add query to the collection
    def add_cached_question(
        self,
        query:str,
        chat_id:str,
        answer:str
        ) -> None:
        """
        Add a question to the cache for similarity matching
        
        Args:
            question: The question text
            chat_id: UUID of the chat history record
            answer: The answer (stored in metadata)
        """
        collection = self.get_or_create_queries_collection()
        collection.add(
            documents=[query],
            metadatas=[{"chat_id": chat_id, "answer": answer[:500]}], # limit answer to 500 characters
            ids=[chat_id]
        )
    
    # search for relevant query
    def find_similar_question(
        self,
        query:str,
        threshold:float=0.15
    ) -> Optional[Tuple[str,float]]:
        """
        Find similar cached questions
        
        Args:
            question: The question to search for
            threshold: Maximum distance for similarity (lower = more similar)
            
        Returns:
            Tuple of (chat_id, distance) if found, None otherwise
        """
        collection = self.get_or_create_queries_collection()
        results = collection.query(
            query_texts=[query],
            n_results=1,
            # include=["metadatas"],
        )
        logger.info(f"Similarity search results: {results}")
        if not results['ids'][0]:
            return None
        distance = results['distances'][0][0]
        if distance < threshold:
            return results['ids'][0][0], distance
        return None
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about ChromaDB collections
        
        Returns:
            Dict with collection statistics
        """
        docs_collection = self.get_or_create_documents_collection()
        query_collection = self.get_or_create_queries_collection()
        return {
            "documents": {
                "count": docs_collection.count(),
                "name": self.DOCUMENT_COLLECTION_NAME
            },
            "queries": {
                "count": query_collection.count(),
                "name": self.QUERY_COLLECTION_NAME
            }
        }
        
# singleton instance of the service
_chroma_service = None

def get_chroma_service() -> ChromaDBService:
    global _chroma_service
    if _chroma_service is None:
        _chroma_service = ChromaDBService()
    return _chroma_service
