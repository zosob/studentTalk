from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import faiss
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
import numpy as np

sentence_model = SentenceTransformer('all-MiniLM-L6-v2')


class CourseKnowledgeBase:
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.index = None
    
    def add_document(self, content: str, source: str):
        # Split into chunks for better retrieval
        chunks = self.chunk_text(content, 500)
        for i, chunk in enumerate(chunks):
            self.documents.append({
                'content': chunk,
                'source': source,
                'chunk_id': i
            })
            embedding = sentence_model.encode([chunk])[0]
            self.embeddings.append(embedding)
        
        # Build FAISS index
        if self.embeddings:
            embeddings_array = np.array(self.embeddings)
            self.index = faiss.IndexFlatIP(embeddings_array.shape[1])
            self.index.add(embeddings_array)
    
    def chunk_text(self, text: str, chunk_size: int) -> List[str]:
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = ' '.join(words[i:i + chunk_size])
            chunks.append(chunk)
        return chunks
    
    def search_similar(self, query: str, top_k: int = 3) -> List[Dict]:
        if not self.index:
            return []
        
        query_embedding = sentence_model.encode([query])
        scores, indices = self.index.search(query_embedding, top_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc['similarity_score'] = float(score)
                results.append(doc)
        
        return results