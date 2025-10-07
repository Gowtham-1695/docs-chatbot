import os
import uuid
import shutil
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.database import get_db, create_tables
from backend.models import UploadedFile, ChatSession, ChatMessage
from backend.document_processor import DocumentProcessor
from backend.rag_service import RAGService
from backend.config import settings

# Create FastAPI app
app = FastAPI(title="Document RAG Chatbot", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Initialize services
document_processor = DocumentProcessor()
rag_service = RAGService()

# Pydantic models for API
class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    response: str
    session_id: str

class FileInfo(BaseModel):
    id: int
    filename: str
    original_filename: str
    upload_timestamp: str
    text_length: int

class SessionInfo(BaseModel):
    session_id: str
    file_id: int
    filename: str
    created_at: str

class MessageInfo(BaseModel):
    message_type: str
    content: str
    timestamp: str

# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()

# Serve frontend files
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
async def read_root():
    return FileResponse("frontend/index.html")

# File upload endpoint
@app.post("/api/upload", response_model=dict)
async def upload_files(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload one or more Word documents."""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    uploaded_files = []
    errors = []
    
    for file in files:
        try:
            # Validate file type
            if not file.filename.lower().endswith(('.docx', '.doc')):
                errors.append(f"{file.filename}: Only Word documents (.docx, .doc) are supported")
                continue
            
            # Check file size
            content = await file.read()
            if len(content) > settings.MAX_FILE_SIZE:
                errors.append(f"{file.filename}: File too large (max {settings.MAX_FILE_SIZE} bytes)")
                continue
            
            # Generate unique filename
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)
            
            # Save file
            with open(file_path, "wb") as buffer:
                buffer.write(content)
            
            # Process document
            try:
                text, chunks, content_hash = document_processor.process_document(file_path)
                
                # Check for duplicate content
                existing_file = db.query(UploadedFile).filter(
                    UploadedFile.content_hash == content_hash
                ).first()
                
                if existing_file:
                    os.remove(file_path)  # Remove duplicate file
                    errors.append(f"{file.filename}: Duplicate content (already uploaded as {existing_file.original_filename})")
                    continue
                
                # Save to database
                db_file = UploadedFile(
                    filename=unique_filename,
                    original_filename=file.filename,
                    file_path=file_path,
                    text_length=len(text),
                    content_hash=content_hash
                )
                db.add(db_file)
                db.commit()
                db.refresh(db_file)
                
                # Generate and store embeddings
                success = rag_service.store_document_embeddings(db, db_file.id, chunks)
                if not success:
                    errors.append(f"{file.filename}: Failed to generate embeddings")
                    continue
                
                uploaded_files.append({
                    "id": db_file.id,
                    "filename": db_file.original_filename,
                    "text_length": db_file.text_length,
                    "chunks_count": len(chunks)
                })
                
            except Exception as e:
                os.remove(file_path)  # Clean up file on processing error
                errors.append(f"{file.filename}: Processing error - {str(e)}")
                continue
                
        except Exception as e:
            errors.append(f"{file.filename}: Upload error - {str(e)}")
            continue
    
    return {
        "uploaded_files": uploaded_files,
        "errors": errors,
        "success_count": len(uploaded_files),
        "error_count": len(errors)
    }

# List uploaded files
@app.get("/api/files", response_model=List[FileInfo])
async def list_files(db: Session = Depends(get_db)):
    """Get list of all uploaded files."""
    files = db.query(UploadedFile).order_by(UploadedFile.upload_timestamp.desc()).all()
    return [
        FileInfo(
            id=file.id,
            filename=file.filename,
            original_filename=file.original_filename,
            upload_timestamp=file.upload_timestamp.isoformat(),
            text_length=file.text_length
        )
        for file in files
    ]

# Start chat session
@app.post("/api/chat/start", response_model=dict)
async def start_chat_session(
    file_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Start a new chat session for a specific file."""
    # Check if file exists
    file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Create new session
    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        file_id=file_id
    )
    db.add(session)
    db.commit()
    
    return {
        "session_id": session_id,
        "file_id": file_id,
        "filename": file.original_filename
    }

# Chat endpoint
@app.post("/api/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """Send a message and get AI response."""
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Verify session exists
    session = db.query(ChatSession).filter(ChatSession.session_id == request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    # Generate response using RAG
    response = rag_service.generate_answer(db, request.session_id, request.message)
    
    return ChatResponse(
        response=response,
        session_id=request.session_id
    )

# Get chat sessions
@app.get("/api/sessions", response_model=List[SessionInfo])
async def get_chat_sessions(db: Session = Depends(get_db)):
    """Get all chat sessions."""
    sessions = db.query(ChatSession).join(UploadedFile).order_by(ChatSession.updated_at.desc()).all()
    return [
        SessionInfo(
            session_id=session.session_id,
            file_id=session.file_id,
            filename=session.file.original_filename,
            created_at=session.created_at.isoformat()
        )
        for session in sessions
    ]

# Get chat history
@app.get("/api/chat/{session_id}/history", response_model=List[MessageInfo])
async def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get chat history for a session."""
    session = db.query(ChatSession).filter(ChatSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    messages = db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id
    ).order_by(ChatMessage.timestamp.asc()).all()
    
    return [
        MessageInfo(
            message_type=msg.message_type,
            content=msg.content,
            timestamp=msg.timestamp.isoformat()
        )
        for msg in messages
    ]

# Delete file
@app.delete("/api/files/{file_id}")
async def delete_file(
    file_id: int,
    db: Session = Depends(get_db)
):
    """Delete a file and all associated data."""
    file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    
    # Delete physical file
    try:
        if os.path.exists(file.file_path):
            os.remove(file.file_path)
    except Exception as e:
        print(f"Error deleting physical file: {str(e)}")
    
    # Delete from database (cascades to chunks and sessions)
    db.delete(file)
    db.commit()
    
    return {"message": "File deleted successfully"}

# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "hf_api_configured": bool(settings.HF_API_KEY),
        "upload_dir": settings.UPLOAD_DIR,
        "max_file_size": settings.MAX_FILE_SIZE
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)