import pytest
import os
import tempfile
from docx import Document
from backend.document_processor import DocumentProcessor

class TestDocumentProcessor:
    
    def setup_method(self):
        self.processor = DocumentProcessor()
    
    def create_test_docx(self, content_paragraphs):
        """Create a test Word document with given content."""
        doc = Document()
        for paragraph in content_paragraphs:
            doc.add_paragraph(paragraph)
        
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.docx')
        doc.save(temp_file.name)
        return temp_file.name
    
    def test_extract_text_from_docx(self):
        """Test text extraction from Word document."""
        test_content = [
            "This is the first paragraph.",
            "This is the second paragraph with more content.",
            "Final paragraph here."
        ]
        
        docx_path = self.create_test_docx(test_content)
        
        try:
            extracted_text = self.processor.extract_text_from_docx(docx_path)
            
            # Check that all paragraphs are extracted
            for paragraph in test_content:
                assert paragraph in extracted_text
            
            # Check that paragraphs are separated by double newlines
            assert "\n\n" in extracted_text
            
        finally:
            os.unlink(docx_path)
    
    def test_extract_text_from_empty_docx(self):
        """Test text extraction from empty document."""
        docx_path = self.create_test_docx([])
        
        try:
            extracted_text = self.processor.extract_text_from_docx(docx_path)
            assert extracted_text == ""
            
        finally:
            os.unlink(docx_path)
    
    def test_chunk_text_small_text(self):
        """Test chunking with text smaller than chunk size."""
        text = "This is a small text that should not be chunked."
        chunks = self.processor.chunk_text(text)
        
        assert len(chunks) == 1
        assert chunks[0][0] == text
        assert chunks[0][1] == 0  # start_char
        assert chunks[0][2] == len(text)  # end_char
    
    def test_chunk_text_large_text(self):
        """Test chunking with text larger than chunk size."""
        # Create text with more words than chunk_size
        words = ["word"] * (self.processor.chunk_size + 100)
        text = " ".join(words)
        
        chunks = self.processor.chunk_text(text)
        
        # Should have multiple chunks
        assert len(chunks) > 1
        
        # Each chunk should be roughly chunk_size words or less
        for chunk_text, start_char, end_char in chunks:
            chunk_words = chunk_text.split()
            assert len(chunk_words) <= self.processor.chunk_size
            assert start_char < end_char
    
    def test_chunk_text_empty(self):
        """Test chunking empty text."""
        chunks = self.processor.chunk_text("")
        assert chunks == []
    
    def test_chunk_text_overlap(self):
        """Test that chunks have proper overlap."""
        # Create text with enough words to require multiple chunks
        words = ["word{}".format(i) for i in range(self.processor.chunk_size + 50)]
        text = " ".join(words)
        
        chunks = self.processor.chunk_text(text)
        
        if len(chunks) > 1:
            # Check that there's overlap between consecutive chunks
            first_chunk_words = chunks[0][0].split()
            second_chunk_words = chunks[1][0].split()
            
            # The last few words of first chunk should appear in second chunk
            overlap_words = first_chunk_words[-self.processor.chunk_overlap:]
            second_chunk_start_words = second_chunk_words[:self.processor.chunk_overlap]
            
            # There should be some overlap
            assert len(set(overlap_words) & set(second_chunk_start_words)) > 0
    
    def test_calculate_content_hash(self):
        """Test content hash calculation."""
        text1 = "This is some test content."
        text2 = "This is some test content."
        text3 = "This is different content."
        
        hash1 = self.processor.calculate_content_hash(text1)
        hash2 = self.processor.calculate_content_hash(text2)
        hash3 = self.processor.calculate_content_hash(text3)
        
        # Same content should have same hash
        assert hash1 == hash2
        
        # Different content should have different hash
        assert hash1 != hash3
        
        # Hash should be a string
        assert isinstance(hash1, str)
        assert len(hash1) == 64  # SHA-256 produces 64-character hex string
    
    def test_process_document_integration(self):
        """Test the complete document processing pipeline."""
        test_content = [
            "This is the first paragraph with some content.",
            "This is the second paragraph with more detailed information about the topic.",
            "Final paragraph concludes the document with summary."
        ]
        
        docx_path = self.create_test_docx(test_content)
        
        try:
            text, chunks, content_hash = self.processor.process_document(docx_path)
            
            # Check extracted text
            assert isinstance(text, str)
            assert len(text) > 0
            for paragraph in test_content:
                assert paragraph in text
            
            # Check chunks
            assert isinstance(chunks, list)
            assert len(chunks) > 0
            
            # Each chunk should be a tuple with (text, start_char, end_char)
            for chunk in chunks:
                assert isinstance(chunk, tuple)
                assert len(chunk) == 3
                assert isinstance(chunk[0], str)  # chunk text
                assert isinstance(chunk[1], int)  # start_char
                assert isinstance(chunk[2], int)  # end_char
                assert chunk[1] <= chunk[2]  # start <= end
            
            # Check content hash
            assert isinstance(content_hash, str)
            assert len(content_hash) == 64
            
        finally:
            os.unlink(docx_path)