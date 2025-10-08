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
        """Retrieve relevant chunks using improved keyword matching."""
        try:
            # Get all chunks for the file
            chunks = db.query(DocumentChunk).filter(DocumentChunk.file_id == file_id).all()
            if not chunks:
                return []
            
            query_lower = query.lower()
            relevant_chunks = []
            
            # Handle specific queries
            if any(word in query_lower for word in ['first page', '1st page', 'page 1', 'beginning', 'start']):
                # Return first few chunks for page-related queries
                for i, chunk in enumerate(chunks[:3]):
                    similarity = 1.0 - (i * 0.1)  # Higher score for earlier chunks
                    relevant_chunks.append((chunk.chunk_text, similarity))
                return relevant_chunks
            
            # Extract meaningful words (remove common stop words)
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'where', 'when', 'why', 'how', 'there', 'here', 'this', 'that', 'these', 'those'}
            query_words = set(re.findall(r'\w+', query_lower)) - stop_words
            
            # If no meaningful words, return first few chunks
            if not query_words:
                for i, chunk in enumerate(chunks[:3]):
                    similarity = 0.8 - (i * 0.1)
                    relevant_chunks.append((chunk.chunk_text, similarity))
                return relevant_chunks
            
            for chunk in chunks:
                chunk_text_lower = chunk.chunk_text.lower()
                chunk_words = set(re.findall(r'\w+', chunk_text_lower)) - stop_words
                
                # Multiple scoring methods
                scores = []
                
                # 1. Exact phrase matching
                if query_lower in chunk_text_lower:
                    scores.append(1.0)
                
                # 2. Word overlap scoring
                if query_words and chunk_words:
                    common_words = query_words.intersection(chunk_words)
                    if common_words:
                        word_similarity = len(common_words) / len(query_words)
                        scores.append(word_similarity)
                
                # 3. Partial word matching (for variations)
                partial_matches = 0
                for query_word in query_words:
                    for chunk_word in chunk_words:
                        if query_word in chunk_word or chunk_word in query_word:
                            partial_matches += 1
                            break
                
                if partial_matches > 0 and query_words:
                    partial_similarity = partial_matches / len(query_words)
                    scores.append(partial_similarity * 0.7)  # Lower weight for partial matches
                
                # 4. Length bonus for substantial chunks
                if len(chunk.chunk_text) > 100:
                    scores.append(0.1)  # Small bonus for longer chunks
                
                # Use the best score
                if scores:
                    final_score = max(scores)
                    relevant_chunks.append((chunk.chunk_text, final_score))
            
            # If no matches found, return first few chunks as fallback
            if not relevant_chunks:
                for i, chunk in enumerate(chunks[:3]):
                    similarity = 0.5 - (i * 0.1)  # Lower base score for fallback
                    relevant_chunks.append((chunk.chunk_text, similarity))
            
            # Sort by similarity and return top 5
            relevant_chunks.sort(key=lambda x: x[1], reverse=True)
            return relevant_chunks[:5]
        
        except Exception as e:
            print(f"Error retrieving relevant chunks: {str(e)}")
            # Return first chunk as absolute fallback
            chunks = db.query(DocumentChunk).filter(DocumentChunk.file_id == file_id).limit(1).all()
            if chunks:
                return [(chunks[0].chunk_text, 0.3)]
            return []
    
    def generate_answer(self, db: Session, session_id: str, query: str) -> str:
        """Generate answer using simple template-based approach."""
        try:
            # Get chat session and file
            session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
            if not session:
                return "Session not found. Please start a new conversation."
            
            # Debug: Check how many chunks we have
            total_chunks = db.query(DocumentChunk).filter(DocumentChunk.file_id == session.file_id).count()
            print(f"Debug: Found {total_chunks} chunks for file_id {session.file_id}")
            
            # Retrieve relevant chunks
            relevant_chunks = self.retrieve_relevant_chunks(db, session.file_id, query)
            print(f"Debug: Query '{query}' returned {len(relevant_chunks)} relevant chunks")
            
            # Generate simple response
            if not relevant_chunks:
                # Fallback: get first chunk if available
                first_chunk = db.query(DocumentChunk).filter(DocumentChunk.file_id == session.file_id).first()
                if first_chunk:
                    print("Debug: No relevant chunks found, using first chunk as fallback")
                    relevant_chunks = [(first_chunk.chunk_text, 0.5)]
                    top_chunks = [chunk[0] for chunk in relevant_chunks]
                    response = self._create_simple_response(query, top_chunks)
                else:
                    response = "I couldn't find any content in the uploaded document. Please make sure the document was processed correctly."
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
        
        query_lower = query.lower()
        
        # Handle specific query types
        if any(word in query_lower for word in ['first page', '1st page', 'page 1', 'beginning', 'start']):
            response_parts = [
                "Here's what I found from the beginning of the document:",
                ""
            ]
        elif any(word in query_lower for word in ['summary', 'summarize', 'overview', 'main points']):
            response_parts = [
                "Here's a summary based on the document content:",
                ""
            ]
        elif '?' in query:
            response_parts = [
                "Based on your question, here's what I found in the document:",
                ""
            ]
        else:
            response_parts = [
                "Here's the relevant information from the document:",
                ""
            ]
        
        # Add the chunks
        for i, chunk in enumerate(chunks[:2], 1):
            # Clean up the chunk text
            clean_chunk = chunk.strip()
            
            # Truncate very long chunks but try to end at sentence boundaries
            if len(clean_chunk) > 400:
                # Try to find a good breaking point
                sentences = re.split(r'[.!?]+', clean_chunk)
                truncated = ""
                for sentence in sentences:
                    if len(truncated + sentence) < 350:
                        truncated += sentence + ". "
                    else:
                        break
                clean_chunk = truncated.strip() + "..."
            
            response_parts.append(f"📄 Section {i}:")
            response_parts.append(clean_chunk)
            response_parts.append("")
        
        if len(chunks) > 2:
            response_parts.append("💡 There are additional relevant sections in the document that might contain more information.")
        
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