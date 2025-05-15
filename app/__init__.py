"""
Video Search API application package
"""

__version__ = "1.0.0"
__author__ = "Your Name"

# 導出常用的模組，方便其他地方導入
from .config import settings
from .db import get_db, init_db
from .chroma_client import ChromaDBClient

# 設定默認的日誌級別
import logging
logging.getLogger(__name__).setLevel(logging.INFO)
