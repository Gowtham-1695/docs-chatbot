import requests
from typing import List, Optional
from backend.config import settings

class LLMService:
    def __init__(self):
        self.api_key = settings.HF_API_KEY
        self.model = settings.LLM_MODEL
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.llm_url = f"{settings.HF_INFERENCE_URL}/{self.model}"
    
    def generate_response(self, query: str, context_chunks: List[str], 
                         conversation_history: List[dict] = None) -> Optional[str]:
        """Generate response using context and conversation history."""
        if not self.api_key:
            raise ValueError("HF_API_KEY not provided")
        
        # Prepare context
        context = "\n\n".join(context_chunks) if context_chunks else ""
        
        # Create prompt with context and conversation history
        prompt = self._create_prompt(query, context, conversation_history)
        
        # Try different models if the current one fails
        models_to_try = [
            "microsoft/DialoGPT-medium",
            "gpt2",
            "distilgpt2"
        ]
        
        for model in models_to_try:
            model_url = f"{self.headers.get('Authorization', '').replace('Bearer ', '') and f'https://api-inference.huggingface.co/models/{model}' or ''}"
            if not model_url:
                continue
                
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 200,
                    "temperature": 0.7,
                    "do_sample": True,
                    "top_p": 0.9,
                    "repetition_penalty": 1.1,
                    "return_full_text": False
                }
            }
            
            try:
                response = requests.post(
                    f"https://api-inference.huggingface.co/models/{model}",
                    headers=self.headers,
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Handle different response formats
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get('generated_text', '')
                    elif isinstance(result, dict):
                        generated_text = result.get('generated_text', '')
                    else:
                        generated_text = str(result)
                    
                    # Clean up the response (remove the original prompt)
                    if generated_text.startswith(prompt):
                        generated_text = generated_text[len(prompt):].strip()
                    
                    if generated_text and len(generated_text.strip()) > 10:
                        return generated_text.strip()
                else:
                    print(f"LLM API error for {model}: {response.status_code} - {response.text}")
                    continue
            
            except Exception as e:
                print(f"Error with model {model}: {str(e)}")
                continue
        
        # If all models fail, return a fallback response
        return self._fallback_response(query, context_chunks)
    
    def _create_prompt(self, query: str, context: str, conversation_history: List[dict] = None) -> str:
        """Create a well-formatted prompt for the LLM."""
        prompt_parts = []
        
        # System instruction
        prompt_parts.append(
            "You are a helpful AI assistant that answers questions based on provided documents. "
            "Use only the information from the given context to answer questions. "
            "If the context doesn't contain enough information to answer the question, "
            "say so politely and suggest what additional information might be needed."
        )
        
        # Add context if available
        if context:
            prompt_parts.append(f"\nContext from documents:\n{context}")
        
        # Add conversation history
        if conversation_history:
            prompt_parts.append("\nConversation history:")
            for msg in conversation_history[-5:]:  # Last 5 messages for context
                role = "Human" if msg['message_type'] == 'user' else "Assistant"
                prompt_parts.append(f"{role}: {msg['content']}")
        
        # Add current query
        prompt_parts.append(f"\nHuman: {query}")
        prompt_parts.append("Assistant:")
        
        return "\n".join(prompt_parts)
    
    def _fallback_response(self, query: str, context_chunks: List[str]) -> str:
        """Provide a fallback response when LLM is unavailable."""
        if not context_chunks:
            return ("I don't have any relevant information in the uploaded documents to answer your question. "
                   "Please make sure you've uploaded documents that contain information related to your query.")
        
        # Simple keyword-based response as fallback
        relevant_info = []
        query_words = query.lower().split()
        
        for chunk in context_chunks[:3]:  # Use top 3 chunks
            chunk_lower = chunk.lower()
            if any(word in chunk_lower for word in query_words):
                relevant_info.append(chunk[:200] + "..." if len(chunk) > 200 else chunk)
        
        if relevant_info:
            return ("Based on the uploaded documents, here's some relevant information:\n\n" + 
                   "\n\n".join(relevant_info))
        else:
            return ("I found some potentially relevant information in your documents, but I'm having trouble "
                   "processing it right now. Please try rephrasing your question or check if your documents "
                   "contain information related to your query.")