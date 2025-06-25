from app.chroma_client import ChromaDBClient

# 初始化 client 與三個 collection
client = ChromaDBClient.get_instance().get_client()
collection_tt = client.get_or_create_collection(name="title_topic_emb")
collection_st = client.get_or_create_collection(name="summary_transcription_emb")
collection_chunk = client.get_or_create_collection(name="transcription_chunks_emb")

def delete_video_id(collection,id):
    collection.delete(where={"video_id": id})
    print("✅ 已刪除 video_id == ",id," 的資料")

def list_video_id(collection,id):
    results = collection.get(where={"video_id": id}, include=["documents", "metadatas"])
    print(f"共找到 {len(results['documents'])} 筆 video_id == ",id," 的資料")
    for i, meta in enumerate(results["metadatas"]):
        print(f"{i+1}. Metadata: {meta}")
if __name__ == "__main__":
    ids = [str(i) for i in range(138, 160)] 
    for id in ids:
        delete_video_id(collection_tt,id)
        delete_video_id(collection_st,id)
        delete_video_id(collection_chunk,id)
        list_video_id(collection_tt,id)
        list_video_id(collection_st,id)
        list_video_id(collection_chunk,id)
