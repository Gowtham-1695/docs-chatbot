from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from backend.models import UploadedFile, DocumentChunk, ChatSession, ChatMessage
from backend.embedding_service import EmbeddingService
from backend.llm_service import LLMService
from backend.config import settings
import json

class RAGService:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.max_chunks_for_context = settings.MAX_CHUNKS_FOR_CONTEXT
    
    def store_document_embeddings(self, db: Session, file_id: int, chunks: List[Tuple[str, int, int]]) -> bool:
        """Generate and store embeddings for document chunks."""
        try:
            # Get embeddings for all chunks
            chunk_texts = [chunk[0] for chunk in chunks]
            embeddings = self.embedding_service.get_embeddings_batch(chunk_texts)
            
            # Store chunks with embeddings
            for i, ((chunk_text, start_char, end_char), embedding) in enumerate(zip(chunks, embeddings)):
                if embedding is None:
                    print(f"Warning: Failed to get embedding for chunk {i}")
                    continue
                
                chunk_record = DocumentChunk(
                    file_id=file_id,
                    chunk_text=chunk_text,
                    chunk_index=i,
                    start_char=start_char,
                    end_char=end_char,
                    embedding_vector=self.embedding_service.embedding_to_string(embedding)
                )
                db.add(chunk_record)
            
            db.commit()
            return True
        except Exception as e:
            print(f"Error storing document embeddings: {str(e)}")
            db.rollback()
            return False
    
    def retrieve_relevant_chunks(self, db: Session, file_id: int, query: str) -> List[Tuple[str, float]]:
        """Retrieve most relevant chunks for a query."""
        try:
            # Get query embedding
            query_embedding = self.embedding_service.get_embedding(query)
            if not query_embedding:
                return []
            
            # Get all chunks for the file
            chunks = db.query(DocumentChunk).filter(DocumentChunk.file_id == file_id).all()
            if not chunks:
                return []
            
            # Extract embeddings and texts
            chunk_embeddings = []
            chunk_texts = []
            
            for chunk in chunks:
                if chunk.embedding_vector:
                    try:
                        embedding = self.embedding_service.string_to_embedding(chunk.embedding_vector)
                        chunk_embeddings.append(embedding)
                        chunk_texts.append(chunk.chunk_text)
                    except Exception as e:
                        print(f"Error parsing embedding for chunk {chunk.id}: {str(e)}")
                        continue
            
            if not chunk_embeddings:
                return []
            
            # Find similar chunks
            similar_chunks = self.embedding_service.find_similar_chunks(
                query_embedding, chunk_embeddings, self.max_chunks_for_context
            )
            
            # Return relevant chunks with similarity scores
            relevant_chunks = []
            for chunk_idx, similarity in similar_chunks:
                if chunk_idx < len(chunk_texts):
                    relevant_chunks.append((chunk_texts[chunk_idx], similarity))
            
            return relevant_chunks
        
        except Exception as e:
            print(f"Error retrieving relevant chunks: {str(e)}")
            return []
    
    def generate_answer(self, db: Session, session_id: str, query: str) -> str:
        """Generate answer using RAG pipeline."""
        try:
            # Get chat session and file
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                return "Session not found. Please start a new conversation."
            
            # Retrieve relevant chunks
            relevant_chunks = self.retrieve_relevant_chunks(db, session.file_id, query)
            
            # Get conversation history
            conversation_history = db.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).order_by(ChatMessage.timestamp.desc()).limit(10).all()
            
            # Reverse to get chronological order
            conversation_history = list(reversed(conversation_history))
            history_dicts = [
                {"message_type": msg.message_type, "content": msg.content}
                for msg in conversation_history
            ]
            
            # Extract chunk texts for context
            context_chunks = [chunk[0] for chunk in relevant_chunks]
            
            # Generate response
            response = self.llm_service.generate_response(
                query, context_chunks, history_dicts
            )
            
            if not response:
                response = self._fallback_response(context_chunks)
            
            # Store the conversation
            self._store_conversation_turn(db, session_id, query, response, relevant_chunks)
            
            return response
        
        except Exception as e:
            print(f"Error generating answer: {str(e)}")
            return "I encountered an error while processing your question. Please try again."
    
    def _store_conversation_turn(self, db: Session, session_id: str, query: str, 
                                response: str, relevant_chunks: List[Tuple[str, float]]):
        """Store user query and assistant response."""
        try:
            # Store user message
            user_message = ChatMessage(
                session_id=session_id,
                message_type="user",
                content=query
            )
            db.add(user_message)
            
            # Store assistant response with context
            context_info = json.dumps([
                {"text": chunk[0][:200] + "..." if len(chunk[0]) > 200 else chunk[0], 
                 "similarity": chunk[1]}
                for chunk in relevant_chunks[:3]  # Store top 3 chunks info
            ])
            
            assistant_message = ChatMessage(
                session_id=session_id,
                message_type="assistant",
                content=response,
                context_chunks=context_info
            )
            db.add(assistant_message)
            
            db.commit()
        except Exception as e:
            print(f"Error storing conversation: {str(e)}")
            db.rollback()
    
    def _fallback_response(self, context_chunks: List[str]) -> str:
        """Provide fallback response when LLM fails."""
        if not context_chunks:
            return ("I don't have any relevant information in the uploaded documents to answer your question. "
                   "Please make sure you've uploaded documents that contain information related to your query.")
        
        return ("I found some relevant information in your documents, but I'm having trouble generating "
               "a proper response right now. Here's what I found:\n\n" + 
               "\n\n".join(chunk[:300] + "..." if len(chunk) > 300 else chunk 
                          for chunk in context_chunks[:2]))