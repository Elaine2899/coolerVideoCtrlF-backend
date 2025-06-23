from fastapi import APIRouter, HTTPException, Depends
from app.chroma_client import ChromaDBClient
from pydantic import BaseModel
from typing import List, Optional
from app.services.llm_expand import generate_related_queries
from app.services.vectordb_search_for_main import search_videos_with_vectorDB
import uuid

router = APIRouter(prefix="/chroma", tags=["vector-search"])

# 資料模型
class EmbeddingRequest(BaseModel):
    video_id: str
    timestamps: List[float]
    transcripts: List[str]

class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 5

# 端點
@router.post("/embed")
async def embed_video_text(request: EmbeddingRequest):
    try:
        collection = ChromaDBClient.get_instance().get_collection()
        
        # 這裡你需要整合嵌入模型，例如 sentence-transformers
        # 這個部分可能需要額外的模組，或者使用外部服務
        # 簡化範例：假設已經有嵌入向量
        import numpy as np
        # 模擬嵌入向量 (實際應用中應該使用真正的嵌入模型)
        fake_embeddings = [np.random.rand(384).tolist() for _ in request.transcripts]
        
        ids = [str(uuid.uuid4()) for _ in range(len(request.transcripts))]
        metadata = [{"video_id": request.video_id, "timestamp": t} for t in request.timestamps]
        
        collection.add(
            ids=ids,
            embeddings=fake_embeddings,
            metadatas=metadata,
            documents=request.transcripts
        )
        
        return {"status": "success", "count": len(request.transcripts)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"嵌入失敗: {str(e)}")

@router.post("/search")
async def search_videos(request: SearchRequest):
    try:
        expanded_queries = generate_related_queries(request.query)
        _, results = search_videos_with_vectorDB(request.query, k=5)

        response = {
            "query": request.query,
            "expanded_queries": expanded_queries,
            "results": [
                {
                    "score": score,
                    "video_id": vid,
                    "title": title,
                    "summary": summary,
                    "url": embed_url
                }
                for score, vid, title, summary, embed_url in results
            ]
        }

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜尋失敗: {str(e)}")