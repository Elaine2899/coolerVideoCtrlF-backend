from .video_routes import router as video_router
from .chroma_routes import router as chroma_router

__all__ = [
    "video_router",
    "chroma_router"
]