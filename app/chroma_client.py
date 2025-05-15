import os
import time
import logging
import chromadb
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_fixed, before_log, after_log
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
    
    @retry(
        stop=stop_after_attempt(settings.CHROMA_RETRIES),
        wait=wait_fixed(settings.CHROMA_RETRY_DELAY),
        before=before_log(logger, logging.INFO),
        after=after_log(logger, logging.ERROR),
    )
    def _init_client(self):
        """Initialize ChromaDB client with improved retry mechanism"""
        try:
            kwargs = {
                "host": settings.CHROMA_HOST,
                "port": settings.CHROMA_PORT,
            }
            
            if settings.CHROMA_API_KEY:
                kwargs["api_key"] = settings.CHROMA_API_KEY
            
            logger.info(f"Attempting to connect to ChromaDB at {settings.CHROMA_URL}")
            return chromadb.HttpClient(**kwargs)
        except Exception as e:
            logger.error(f"ChromaDB connection attempt failed: {str(e)}")
            raise

    def __init__(self):
        self._client = self._init_client()
        logger.info(f"ChromaDB client initialized with URL: {settings.CHROMA_URL}")
    
    def get_client(self):
        if not self._client:
            self._client = self._init_client()
        return self._client
    
    def get_collection(self, collection_name: str = "video_embeddings"):
        try:
            return self._client.get_or_create_collection(name=collection_name)
        except Exception as e:
            logger.error(f"Failed to get collection {collection_name}: {str(e)}")
            raise