import chromadb
from fastapi import FastAPI
from .config import settings

class ChromaDBClient:
    _instance = None
    _client = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = ChromaDBClient()
        return cls._instance
    
    def __init__(self):
        self._client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        
    def get_client(self):
        return self._client
    
    def get_collection(self, collection_name="video_embeddings"):
        return self._client.get_or_create_collection(name=collection_name)

# 在其他檔案中使用:
# from app.chroma_client import ChromaDBClient
# chroma_client = ChromaDBClient.get_instance().get_client()
# collection = ChromaDBClient.get_instance().get_collection()