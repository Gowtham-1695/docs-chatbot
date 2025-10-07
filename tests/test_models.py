import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from backend.models import UploadedFile, DocumentChunk, ChatSession, ChatMessage

class TestModels:
    
    def test_uploaded_file_creation(self, test_db):
        """Test creating an UploadedFile record."""
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000,
            content_hash="abc123def456"
        )
        
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        assert file_record.id is not None
        assert file_record.filename == "test_file.docx"
        assert file_record.original_filename == "original_test.docx"
        assert file_record.file_path == "/path/to/test_file.docx"
        assert file_record.text_length == 1000
        assert file_record.content_hash == "abc123def456"
        assert file_record.upload_timestamp is not None
        assert isinstance(file_record.upload_timestamp, datetime)
    
    def test_uploaded_file_required_fields(self, test_db):
        """Test that required fields are enforced."""
        # Missing required fields should raise an error
        file_record = UploadedFile()
        test_db.add(file_record)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_document_chunk_creation(self, test_db):
        """Test creating a DocumentChunk record."""
        # First create a file
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        # Create chunk
        chunk = DocumentChunk(
            file_id=file_record.id,
            chunk_text="This is a test chunk of text.",
            chunk_index=0,
            start_char=0,
            end_char=29,
            embedding_vector='[0.1, 0.2, 0.3]'
        )
        
        test_db.add(chunk)
        test_db.commit()
        test_db.refresh(chunk)
        
        assert chunk.id is not None
        assert chunk.file_id == file_record.id
        assert chunk.chunk_text == "This is a test chunk of text."
        assert chunk.chunk_index == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 29
        assert chunk.embedding_vector == '[0.1, 0.2, 0.3]'
    
    def test_document_chunk_file_relationship(self, test_db):
        """Test the relationship between DocumentChunk and UploadedFile."""
        # Create file
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        # Create chunk
        chunk = DocumentChunk(
            file_id=file_record.id,
            chunk_text="Test chunk",
            chunk_index=0,
            start_char=0,
            end_char=10
        )
        test_db.add(chunk)
        test_db.commit()
        test_db.refresh(chunk)
        
        # Test relationship
        assert chunk.file == file_record
        assert chunk in file_record.chunks
    
    def test_chat_session_creation(self, test_db):
        """Test creating a ChatSession record."""
        # Create file first
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        # Create session
        session = ChatSession(
            session_id="test-session-123",
            file_id=file_record.id
        )
        
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        
        assert session.id is not None
        assert session.session_id == "test-session-123"
        assert session.file_id == file_record.id
        assert session.created_at is not None
        assert session.updated_at is not None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.updated_at, datetime)
    
    def test_chat_session_unique_session_id(self, test_db):
        """Test that session_id must be unique."""
        # Create file
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        # Create first session
        session1 = ChatSession(
            session_id="duplicate-session-id",
            file_id=file_record.id
        )
        test_db.add(session1)
        test_db.commit()
        
        # Try to create second session with same session_id
        session2 = ChatSession(
            session_id="duplicate-session-id",
            file_id=file_record.id
        )
        test_db.add(session2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_chat_message_creation(self, test_db):
        """Test creating a ChatMessage record."""
        # Create file and session first
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        session = ChatSession(
            session_id="test-session-123",
            file_id=file_record.id
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        
        # Create message
        message = ChatMessage(
            session_id=session.session_id,
            message_type="user",
            content="This is a test message.",
            context_chunks='[{"text": "relevant chunk", "similarity": 0.8}]'
        )
        
        test_db.add(message)
        test_db.commit()
        test_db.refresh(message)
        
        assert message.id is not None
        assert message.session_id == session.session_id
        assert message.message_type == "user"
        assert message.content == "This is a test message."
        assert message.context_chunks == '[{"text": "relevant chunk", "similarity": 0.8}]'
        assert message.timestamp is not None
        assert isinstance(message.timestamp, datetime)
    
    def test_chat_message_session_relationship(self, test_db):
        """Test the relationship between ChatMessage and ChatSession."""
        # Create file and session
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        session = ChatSession(
            session_id="test-session-123",
            file_id=file_record.id
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        
        # Create messages
        message1 = ChatMessage(
            session_id=session.session_id,
            message_type="user",
            content="First message"
        )
        message2 = ChatMessage(
            session_id=session.session_id,
            message_type="assistant",
            content="Response message"
        )
        
        test_db.add_all([message1, message2])
        test_db.commit()
        test_db.refresh(message1)
        test_db.refresh(message2)
        
        # Test relationships
        assert message1.session == session
        assert message2.session == session
        assert message1 in session.messages
        assert message2 in session.messages
        assert len(session.messages) == 2
    
    def test_cascade_delete_file(self, test_db):
        """Test that deleting a file cascades to chunks and sessions."""
        # Create file with chunks and session
        file_record = UploadedFile(
            filename="test_file.docx",
            original_filename="original_test.docx",
            file_path="/path/to/test_file.docx",
            text_length=1000
        )
        test_db.add(file_record)
        test_db.commit()
        test_db.refresh(file_record)
        
        # Add chunk
        chunk = DocumentChunk(
            file_id=file_record.id,
            chunk_text="Test chunk",
            chunk_index=0,
            start_char=0,
            end_char=10
        )
        test_db.add(chunk)
        
        # Add session with message
        session = ChatSession(
            session_id="test-session-123",
            file_id=file_record.id
        )
        test_db.add(session)
        test_db.commit()
        test_db.refresh(session)
        
        message = ChatMessage(
            session_id=session.session_id,
            message_type="user",
            content="Test message"
        )
        test_db.add(message)
        test_db.commit()
        
        # Verify everything exists
        assert test_db.query(UploadedFile).count() == 1
        assert test_db.query(DocumentChunk).count() == 1
        assert test_db.query(ChatSession).count() == 1
        assert test_db.query(ChatMessage).count() == 1
        
        # Delete the file
        test_db.delete(file_record)
        test_db.commit()
        
        # Verify cascade delete worked
        assert test_db.query(UploadedFile).count() == 0
        assert test_db.query(DocumentChunk).count() == 0
        assert test_db.query(ChatSession).count() == 0
        assert test_db.query(ChatMessage).count() == 0