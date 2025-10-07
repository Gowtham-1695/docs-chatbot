"""
Simple RAG implementation that works without complex API calls
"""
import re
from typing import List, Tuple
from sqlalchemy.orm import Session
from backend.models import UploadedFile, DocumentChunk, ChatSession, ChatMessage
import json

class SimpleRAGService:
    def __init__(self):
        pass
    
    def store_document_embeddings(self, db: Session, file_id: int, chunks: List[Tuple[str, int, int]]) -> bool:
        """Store document chunks without embeddings (using simple text matching instead)."""
        try:
            # Store chunks without embeddings for now
            for i, (chunk_text, start_char, end_char) in enumerate(chunks):
                chunk_record = DocumentChunk(
                    file_id=file_id,
                    chunk_text=chunk_text,
                    chunk_index=i,
                    start_char=start_char,
                    end_char=end_char,
                    embedding_vector=None  # No embeddings for now
                )
                db.add(chunk_record)
            
            db.commit()
            return True
        except Exception as e:
            print(f"Error storing document chunks: {str(e)}")
            db.rollback()
            return False
    
    def retrieve_relevant_chunks(self, db: Session, file_id: int, query: str) -> List[Tuple[str, float]]:
        """Retrieve relevant chunks using simple keyword matching."""
        try:
            # Get all chunks for the file
            chunks = db.query(DocumentChunk).filter(DocumentChunk.file_id == file_id).all()
            if not chunks:
                return []
            
            # Simple keyword-based matching
            query_words = set(re.findall(r'\w+', query.lower()))
            relevant_chunks = []
            
            for chunk in chunks:
                chunk_words = set(re.findall(r'\w+', chunk.chunk_text.lower()))
                
                # Calculate simple similarity based on common words
                common_words = query_words.intersection(chunk_words)
                if common_words:
                    similarity = len(common_words) / len(query_words.union(chunk_words))
                    relevant_chunks.append((chunk.chunk_text, similarity))
            
            # Sort by similarity and return top 5
            relevant_chunks.sort(key=lambda x: x[1], reverse=True)
            return relevant_chunks[:5]
        
        except Exception as e:
            print(f"Error retrieving relevant chunks: {str(e)}")
            return []
    
    def generate_answer(self, db: Session, session_id: str, query: str) -> str:
        """Generate answer using simple template-based approach."""
        try:
            # Get chat session and file
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                return "Session not found. Please start a new conversation."
            
            # Retrieve relevant chunks
            relevant_chunks = self.retrieve_relevant_chunks(db, session.file_id, query)
            
            # Generate simple response
            if not relevant_chunks:
                response = "I couldn't find specific information about your question in the uploaded document. Could you try rephrasing your question or asking about different topics covered in the document?"
            else:
                # Create a simple response based on the most relevant chunks
                top_chunks = [chunk[0] for chunk in relevant_chunks[:3]]
                response = self._create_simple_response(query, top_chunks)
            
            # Store the conversation
            self._store_conversation_turn(db, session_id, query, response, relevant_chunks)
            
            return response
        
        except Exception as e:
            print(f"Error generating answer: {str(e)}")
            return "I encountered an error while processing your question. Please try again."
    
    def _create_simple_response(self, query: str, chunks: List[str]) -> str:
        """Create a simple response based on relevant chunks."""
        if not chunks:
            return "I couldn't find relevant information in the document to answer your question."
        
        # Simple template-based response
        response_parts = [
            "Based on the document, here's what I found:",
            ""
        ]
        
        for i, chunk in enumerate(chunks[:2], 1):
            # Truncate long chunks
            truncated_chunk = chunk[:300] + "..." if len(chunk) > 300 else chunk
            response_parts.append(f"{i}. {truncated_chunk}")
            response_parts.append("")
        
        if len(chunks) > 2:
            response_parts.append("There are additional relevant sections in the document that might contain more information about your question.")
        
        return "\n".join(response_parts)
    
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
                for chunk in relevant_chunks[:3]
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