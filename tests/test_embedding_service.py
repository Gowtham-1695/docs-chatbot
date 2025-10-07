import pytest
import json
from unittest.mock import Mock, patch
from backend.embedding_service import EmbeddingService

class TestEmbeddingService:
    
    def setup_method(self):
        self.service = EmbeddingService()
    
    def test_embedding_to_string(self):
        """Test converting embedding to JSON string."""
        embedding = [0.1, 0.2, 0.3, -0.1, -0.2]
        result = self.service.embedding_to_string(embedding)
        
        assert isinstance(result, str)
        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed == embedding
    
    def test_string_to_embedding(self):
        """Test converting JSON string back to embedding."""
        embedding = [0.1, 0.2, 0.3, -0.1, -0.2]
        embedding_str = json.dumps(embedding)
        
        result = self.service.string_to_embedding(embedding_str)
        assert result == embedding
    
    def test_find_similar_chunks_empty_input(self):
        """Test finding similar chunks with empty input."""
        query_embedding = [0.1, 0.2, 0.3]
        chunk_embeddings = []
        
        result = self.service.find_similar_chunks(query_embedding, chunk_embeddings)
        assert result == []
    
    def test_find_similar_chunks_empty_query(self):
        """Test finding similar chunks with empty query embedding."""
        query_embedding = []
        chunk_embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        
        result = self.service.find_similar_chunks(query_embedding, chunk_embeddings)
        assert result == []
    
    def test_find_similar_chunks_valid_input(self):
        """Test finding similar chunks with valid input."""
        query_embedding = [1.0, 0.0, 0.0]
        chunk_embeddings = [
            [1.0, 0.0, 0.0],  # Identical - should be most similar
            [0.0, 1.0, 0.0],  # Orthogonal - should be less similar
            [0.5, 0.5, 0.0],  # Partially similar
        ]
        
        result = self.service.find_similar_chunks(query_embedding, chunk_embeddings, top_k=2)
        
        assert len(result) == 2
        # Results should be sorted by similarity (descending)
        assert result[0][1] >= result[1][1]  # First should be more similar
        
        # The identical embedding should be first
        assert result[0][0] == 0  # Index of identical embedding
        assert result[0][1] > 0.9  # Very high similarity
    
    def test_find_similar_chunks_top_k_limit(self):
        """Test that top_k parameter limits results correctly."""
        query_embedding = [1.0, 0.0, 0.0]
        chunk_embeddings = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.8, 0.2, 0.0],
            [0.7, 0.3, 0.0],
            [0.6, 0.4, 0.0],
        ]
        
        result = self.service.find_similar_chunks(query_embedding, chunk_embeddings, top_k=3)
        
        assert len(result) == 3
        # Should return top 3 most similar
        similarities = [sim for _, sim in result]
        assert similarities == sorted(similarities, reverse=True)
    
    @patch('requests.post')
    def test_get_embedding_success(self, mock_post):
        """Test successful embedding retrieval."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        mock_post.return_value = mock_response
        
        result = self.service.get_embedding("test text")
        
        assert result == [0.1, 0.2, 0.3, 0.4, 0.5]
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_get_embedding_api_error(self, mock_post):
        """Test embedding retrieval with API error."""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response
        
        result = self.service.get_embedding("test text")
        
        assert result is None
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_get_embedding_network_error(self, mock_post):
        """Test embedding retrieval with network error."""
        # Mock network error
        mock_post.side_effect = Exception("Network error")
        
        result = self.service.get_embedding("test text")
        
        assert result is None
        mock_post.assert_called_once()
    
    @patch('requests.post')
    def test_get_embedding_different_response_format(self, mock_post):
        """Test embedding retrieval with different API response format."""
        # Mock response with embedding in dict format
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"embedding": [0.1, 0.2, 0.3]}]
        mock_post.return_value = mock_response
        
        result = self.service.get_embedding("test text")
        
        assert result == [0.1, 0.2, 0.3]
        mock_post.assert_called_once()
    
    def test_get_embedding_no_api_key(self):
        """Test embedding retrieval without API key."""
        # Temporarily remove API key
        original_key = self.service.api_key
        self.service.api_key = ""
        
        try:
            with pytest.raises(ValueError, match="HF_API_KEY not provided"):
                self.service.get_embedding("test text")
        finally:
            self.service.api_key = original_key
    
    @patch('requests.post')
    def test_get_embeddings_batch(self, mock_post):
        """Test batch embedding retrieval."""
        # Mock successful API responses
        mock_response = Mock()
        mock_response.status_code = 200
        
        def side_effect(*args, **kwargs):
            # Return different embeddings for different texts
            payload = kwargs.get('json', {})
            text = payload.get('inputs', '')
            if 'first' in text:
                mock_response.json.return_value = [[0.1, 0.2, 0.3]]
            else:
                mock_response.json.return_value = [[0.4, 0.5, 0.6]]
            return mock_response
        
        mock_post.side_effect = side_effect
        
        texts = ["first text", "second text"]
        results = self.service.get_embeddings_batch(texts)
        
        assert len(results) == 2
        assert results[0] == [0.1, 0.2, 0.3]
        assert results[1] == [0.4, 0.5, 0.6]
        assert mock_post.call_count == 2