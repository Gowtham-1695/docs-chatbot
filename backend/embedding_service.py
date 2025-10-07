import json
import requests
from typing import List, Optional, Tuple
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from backend.config import settings

class EmbeddingService:
    def __init__(self):
        self.api_key = settings.HF_API_KEY
        self.embedding_model = settings.EMBEDDING_MODEL
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.embedding_url = f"{settings.HF_INFERENCE_URL}/{self.embedding_model}"
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding for a single text using Hugging Face API."""
        if not self.api_key:
            raise ValueError("HF_API_KEY not provided")
        
        # Use the correct format for sentence transformers
        payload = {"inputs": [text]}  # Note: wrapped in list
        
        try:
            response = requests.post(
                self.embedding_url,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], list):
                        return result[0]  # Direct embedding
                    elif isinstance(result[0], dict) and 'embedding' in result[0]:
                        return result[0]['embedding']
                return result
            else:
                print(f"Embedding API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting embedding: {str(e)}")
            return None
    
    def get_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Get embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def find_similar_chunks(self, query_embedding: List[float], 
                          chunk_embeddings: List[List[float]], 
                          top_k: int = 5) -> List[Tuple[int, float]]:
        """Find most similar chunks using cosine similarity."""
        if not query_embedding or not chunk_embeddings:
            return []
        
        try:
            query_vec = np.array(query_embedding).reshape(1, -1)
            chunk_vecs = np.array(chunk_embeddings)
            
            similarities = cosine_similarity(query_vec, chunk_vecs)[0]
            
            # Get top-k most similar chunks
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            return [(int(idx), float(similarities[idx])) for idx in top_indices]
        except Exception as e:
            print(f"Error finding similar chunks: {str(e)}")
            return []
    
    def embedding_to_string(self, embedding: List[float]) -> str:
        """Convert embedding to JSON string for storage."""
        return json.dumps(embedding)
    
    def string_to_embedding(self, embedding_str: str) -> List[float]:
        """Convert JSON string back to embedding."""
        return json.loads(embedding_str)