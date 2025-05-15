import os
import logging
import chromadb
from typing import Optional
from .config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChromaDBClient:
    _instance = None
    _client = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ChromaDBClient()
        return cls._instance
    
    def __init__(self):
        try:
            kwargs = {
                "host": settings.CHROMA_HOST,
                "port": settings.CHROMA_PORT,
            }
            
            if settings.CHROMA_API_KEY:
                kwargs["api_key"] = settings.CHROMA_API_KEY
                
            self._client = chromadb.HttpClient(**kwargs)
            logger.info(f"ChromaDB client initialized with URL: {settings.CHROMA_URL}")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def get_client(self):
        return self._client
    
    def get_collection(self, collection_name: str = "video_embeddings"):
        try:
            return self._client.get_or_create_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {e}")
            raise