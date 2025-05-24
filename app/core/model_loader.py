from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoTokenizer
from bertopic import BERTopic
import torch

# 全域變數
title_topic_embedder = None
summary_embedder = None
topic_model = None
summarizer = None
tokenizer = None

def load_models():
    global title_topic_embedder, summary_embedder, topic_model, summarizer, tokenizer
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    title_topic_embedder = SentenceTransformer('paraphrase-MiniLM-L6-v2', device=device)
    summary_embedder = SentenceTransformer('BAAI/bge-m3', device=device)
    topic_model = BERTopic.load("MaartenGr/BERTopic_Wikipedia", embedding_model=title_topic_embedder)
    summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-6-6", device=0 if device == 'cuda' else -1)
    tokenizer = AutoTokenizer.from_pretrained("sshleifer/distilbart-cnn-6-6")
