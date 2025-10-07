import pytest
import os
import tempfile
import json
from io import BytesIO
from docx import Document
from fastapi.testclient import TestClient

from backend.models import UploadedFile, ChatSession, ChatMessage

class TestAPIEndpoints:
    
    def create_test_docx_file(self, content_paragraphs, filename="test.docx"):
        """Create a test Word document file."""
        doc = Document()
        for paragraph in content_paragraphs:
            doc.add_paragraph(paragraph)
        
        file_bytes = BytesIO()
        doc.save(file_bytes)
        file_bytes.seek(0)
        
        return file_bytes.getvalue(), filename
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/api/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "hf_api_configured" in data
        assert "upload_dir" in data
        assert "max_file_size" in data
    
    def test_upload_single_file(self, client, temp_upload_dir, test_db):
        """Test uploading a single Word document."""
        content, filename = self.create_test_docx_file([
            "This is a test document.",
            "It contains multiple paragraphs.",
            "This is for testing purposes."
        ])
        
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert "uploaded_files" in data
        assert "errors" in data
        assert data["success_count"] == 1
        assert data["error_count"] == 0
        assert len(data["uploaded_files"]) == 1
        
        uploaded_file = data["uploaded_files"][0]
        assert uploaded_file["filename"] == filename
        assert uploaded_file["text_length"] > 0
        assert uploaded_file["chunks_count"] > 0
        
        # Verify file is in database
        db_file = test_db.query(UploadedFile).first()
        assert db_file is not None
        assert db_file.original_filename == filename
    
    def test_upload_multiple_files(self, client, temp_upload_dir, test_db):
        """Test uploading multiple Word documents."""
        files_data = [
            self.create_test_docx_file(["First document content."], "doc1.docx"),
            self.create_test_docx_file(["Second document content."], "doc2.docx")
        ]
        
        files = [
            ("files", (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
            for content, filename in files_data
        ]
        
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        assert len(data["uploaded_files"]) == 2
        
        # Verify files are in database
        db_files = test_db.query(UploadedFile).all()
        assert len(db_files) == 2
    
    def test_upload_invalid_file_type(self, client, temp_upload_dir):
        """Test uploading non-Word document."""
        files = {"files": ("test.txt", b"This is a text file", "text/plain")}
        
        response = client.post("/api/upload", files=files)
        assert response.status_code == 200
        
        data = response.json()
        assert data["success_count"] == 0
        assert data["error_count"] == 1
        assert len(data["errors"]) == 1
        assert "Only Word documents" in data["errors"][0]
    
    def test_upload_duplicate_content(self, client, temp_upload_dir, test_db):
        """Test uploading duplicate content."""
        content, filename = self.create_test_docx_file(["Duplicate content test."])
        
        # Upload first file
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response1 = client.post("/api/upload", files=files)
        assert response1.status_code == 200
        assert response1.json()["success_count"] == 1
        
        # Upload same content with different filename
        files = {"files": ("duplicate.docx", content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        response2 = client.post("/api/upload", files=files)
        assert response2.status_code == 200
        
        data = response2.json()
        assert data["success_count"] == 0
        assert data["error_count"] == 1
        assert "Duplicate content" in data["errors"][0]
    
    def test_list_files_empty(self, client, test_db):
        """Test listing files when no files uploaded."""
        response = client.get("/api/files")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_files_with_data(self, client, temp_upload_dir, test_db):
        """Test listing files after uploading."""
        # Upload a file first
        content, filename = self.create_test_docx_file(["Test content for listing."])
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        upload_response = client.post("/api/upload", files=files)
        assert upload_response.status_code == 200
        
        # List files
        response = client.get("/api/files")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        
        file_info = data[0]
        assert "id" in file_info
        assert file_info["original_filename"] == filename
        assert "upload_timestamp" in file_info
        assert file_info["text_length"] > 0
    
    def test_start_chat_session(self, client, temp_upload_dir, test_db):
        """Test starting a chat session."""
        # Upload a file first
        content, filename = self.create_test_docx_file(["Content for chat testing."])
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        upload_response = client.post("/api/upload", files=files)
        file_id = upload_response.json()["uploaded_files"][0]["id"]
        
        # Start chat session
        response = client.post("/api/chat/start", data={"file_id": file_id})
        assert response.status_code == 200
        
        data = response.json()
        assert "session_id" in data
        assert data["file_id"] == file_id
        assert data["filename"] == filename
        
        # Verify session in database
        session = test_db.query(ChatSession).first()
        assert session is not None
        assert session.session_id == data["session_id"]
        assert session.file_id == file_id
    
    def test_start_chat_session_invalid_file(self, client, test_db):
        """Test starting chat session with invalid file ID."""
        response = client.post("/api/chat/start", data={"file_id": 999})
        assert response.status_code == 404
        
        data = response.json()
        assert "File not found" in data["detail"]
    
    def test_chat_invalid_session(self, client, test_db):
        """Test chatting with invalid session ID."""
        chat_data = {
            "session_id": "invalid-session-id",
            "message": "Test message"
        }
        
        response = client.post("/api/chat", json=chat_data)
        assert response.status_code == 404
        
        data = response.json()
        assert "Chat session not found" in data["detail"]
    
    def test_chat_empty_message(self, client, temp_upload_dir, test_db):
        """Test chatting with empty message."""
        # Setup: upload file and start session
        content, filename = self.create_test_docx_file(["Test content."])
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        upload_response = client.post("/api/upload", files=files)
        file_id = upload_response.json()["uploaded_files"][0]["id"]
        
        session_response = client.post("/api/chat/start", data={"file_id": file_id})
        session_id = session_response.json()["session_id"]
        
        # Test empty message
        chat_data = {
            "session_id": session_id,
            "message": ""
        }
        
        response = client.post("/api/chat", json=chat_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "Message cannot be empty" in data["detail"]
    
    def test_get_chat_sessions_empty(self, client, test_db):
        """Test getting chat sessions when none exist."""
        response = client.get("/api/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_chat_sessions_with_data(self, client, temp_upload_dir, test_db):
        """Test getting chat sessions after creating some."""
        # Setup: upload file and start session
        content, filename = self.create_test_docx_file(["Session test content."])
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        upload_response = client.post("/api/upload", files=files)
        file_id = upload_response.json()["uploaded_files"][0]["id"]
        
        session_response = client.post("/api/chat/start", data={"file_id": file_id})
        session_id = session_response.json()["session_id"]
        
        # Get sessions
        response = client.get("/api/sessions")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 1
        
        session_info = data[0]
        assert session_info["session_id"] == session_id
        assert session_info["file_id"] == file_id
        assert session_info["filename"] == filename
        assert "created_at" in session_info
    
    def test_get_chat_history_invalid_session(self, client, test_db):
        """Test getting chat history for invalid session."""
        response = client.get("/api/chat/invalid-session/history")
        assert response.status_code == 404
        
        data = response.json()
        assert "Session not found" in data["detail"]
    
    def test_get_chat_history_empty(self, client, temp_upload_dir, test_db):
        """Test getting chat history for session with no messages."""
        # Setup: upload file and start session
        content, filename = self.create_test_docx_file(["History test content."])
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        upload_response = client.post("/api/upload", files=files)
        file_id = upload_response.json()["uploaded_files"][0]["id"]
        
        session_response = client.post("/api/chat/start", data={"file_id": file_id})
        session_id = session_response.json()["session_id"]
        
        # Get history
        response = client.get(f"/api/chat/{session_id}/history")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_delete_file_invalid_id(self, client, test_db):
        """Test deleting non-existent file."""
        response = client.delete("/api/files/999")
        assert response.status_code == 404
        
        data = response.json()
        assert "File not found" in data["detail"]
    
    def test_delete_file_success(self, client, temp_upload_dir, test_db):
        """Test successful file deletion."""
        # Upload a file first
        content, filename = self.create_test_docx_file(["Content to be deleted."])
        files = {"files": (filename, content, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
        
        upload_response = client.post("/api/upload", files=files)
        file_id = upload_response.json()["uploaded_files"][0]["id"]
        
        # Delete the file
        response = client.delete(f"/api/files/{file_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert "File deleted successfully" in data["message"]
        
        # Verify file is deleted from database
        db_file = test_db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        assert db_file is None