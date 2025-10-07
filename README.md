# Document RAG Chatbot

A web application that allows users to upload Word documents and chat with their content using AI. Built with FastAPI backend, SQLAlchemy ORM, and Hugging Face models for RAG (Retrieval-Augmented Generation) capabilities.

## 🚀 Features

- **Document Upload**: Upload single or multiple Word documents (.docx, .doc)
- **Text Extraction**: Extract and process text from Word documents
- **RAG Pipeline**: Chunk documents, generate embeddings, and retrieve relevant context
- **AI Chat**: Chat with document content using Hugging Face models
- **Conversation History**: Persistent chat sessions with full conversation history
- **Duplicate Detection**: Automatic detection and prevention of duplicate document uploads
- **Modern UI**: Clean, responsive web interface
- **RESTful API**: Well-documented API endpoints

## 🏗️ Architecture

### Backend Components

1. **FastAPI Application** (`backend/main.py`)
   - RESTful API endpoints
   - File upload handling
   - Chat session management
   - CORS middleware for frontend integration

2. **Database Models** (`backend/models.py`)
   - `UploadedFile`: Document metadata and file information
   - `DocumentChunk`: Text chunks with embeddings
   - `ChatSession`: Chat session management
   - `ChatMessage`: Individual messages with context

3. **Document Processing** (`backend/document_processor.py`)
   - Text extraction from Word documents
   - Intelligent text chunking with overlap
   - Content deduplication using SHA-256 hashing

4. **RAG Pipeline** (`backend/rag_service.py`)
   - Embedding generation and storage
   - Semantic similarity search
   - Context retrieval for LLM queries
   - Conversation management

5. **AI Services**
   - `EmbeddingService`: Hugging Face embeddings API integration
   - `LLMService`: Text generation using Hugging Face models

### Frontend Components

- **Single Page Application**: HTML/CSS/JavaScript
- **File Upload Interface**: Drag-and-drop and click-to-browse
- **Chat Interface**: Real-time messaging with conversation history
- **Session Management**: Browse and resume previous conversations
- **Responsive Design**: Works on desktop and mobile devices

### Database Schema

```sql
uploaded_files
├── id (Primary Key)
├── filename (Unique filename)
├── original_filename (User's original filename)
├── file_path (Physical file location)
├── upload_timestamp (When uploaded)
├── text_length (Character count)
└── content_hash (SHA-256 for deduplication)

document_chunks
├── id (Primary Key)
├── file_id (Foreign Key → uploaded_files.id)
├── chunk_text (Text content)
├── chunk_index (Order in document)
├── start_char, end_char (Position in original text)
└── embedding_vector (JSON-encoded embedding)

chat_sessions
├── id (Primary Key)
├── session_id (UUID)
├── file_id (Foreign Key → uploaded_files.id)
├── created_at, updated_at (Timestamps)

chat_messages
├── id (Primary Key)
├── session_id (Foreign Key → chat_sessions.session_id)
├── message_type ('user' or 'assistant')
├── content (Message text)
├── timestamp (When sent)
└── context_chunks (JSON-encoded relevant chunks)
```

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8+
- Hugging Face API key ([Get one here](https://huggingface.co/settings/tokens))

### Local Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd document-rag-chatbot
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file and add your Hugging Face API key
   ```

5. **Create upload directory**
   ```bash
   mkdir uploads
   ```

6. **Run the application**
   ```bash
   python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Access the application**
   - Open your browser and go to `http://localhost:8000`
   - The API documentation is available at `http://localhost:8000/docs`

### Environment Variables

Create a `.env` file in the root directory:

```env
# Required: Hugging Face API Configuration
HF_API_KEY=your_hugging_face_api_key_here

# Optional: Database Configuration
DATABASE_URL=sqlite:///./chatbot.db

# Optional: API Configuration
API_HOST=0.0.0.0
API_PORT=8000

# Optional: File Upload Configuration
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=10485760  # 10MB in bytes

# Optional: RAG Configuration
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MAX_CHUNKS_FOR_CONTEXT=5

# Optional: Model Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
LLM_MODEL=microsoft/DialoGPT-medium
```

## 📚 API Documentation

### File Upload

**POST** `/api/upload`
- Upload one or more Word documents
- **Form Data**: `files` (multipart/form-data)
- **Response**: Upload results with success/error counts

### File Management

**GET** `/api/files`
- List all uploaded files
- **Response**: Array of file information

**DELETE** `/api/files/{file_id}`
- Delete a file and all associated data
- **Response**: Success confirmation

### Chat Operations

**POST** `/api/chat/start`
- Start a new chat session for a file
- **Form Data**: `file_id` (integer)
- **Response**: Session information

**POST** `/api/chat`
- Send a message and get AI response
- **JSON Body**: `{"session_id": "uuid", "message": "text"}`
- **Response**: AI-generated response

**GET** `/api/sessions`
- List all chat sessions
- **Response**: Array of session information

**GET** `/api/chat/{session_id}/history`
- Get conversation history for a session
- **Response**: Array of messages

### Health Check

**GET** `/api/health`
- Check API status and configuration
- **Response**: System health information

## 🧪 Testing

The project includes comprehensive unit and integration tests.

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend

# Run specific test file
pytest tests/test_api_endpoints.py

# Run with verbose output
pytest -v
```

### Test Structure

- `tests/test_api_endpoints.py`: API endpoint testing
- `tests/test_document_processor.py`: Document processing logic
- `tests/test_embedding_service.py`: Embedding service functionality
- `tests/test_models.py`: Database model testing
- `tests/conftest.py`: Test configuration and fixtures

## 🔧 Configuration

### Chunking Strategy

The system uses intelligent text chunking with the following parameters:

- **Chunk Size**: 512 words (configurable via `CHUNK_SIZE`)
- **Overlap**: 50 words between chunks (configurable via `CHUNK_OVERLAP`)
- **Context Limit**: Top 5 most relevant chunks for LLM context

### Model Selection

**Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
- Fast, efficient sentence embeddings
- Good balance of speed and quality
- 384-dimensional embeddings

**LLM Model**: `microsoft/DialoGPT-medium`
- Conversational AI optimized for dialogue
- Good performance for Q&A tasks
- Reasonable inference speed

### Performance Considerations

- **File Size Limit**: 10MB per file (configurable)
- **Batch Processing**: Embeddings generated in batches for efficiency
- **Caching**: Embeddings stored in database to avoid recomputation
- **Memory Usage**: Optimized for systems with limited GPU/CPU resources

## 🚀 Deployment

### Production Deployment

1. **Set production environment variables**
   ```bash
   export HF_API_KEY=your_production_api_key
   export DATABASE_URL=postgresql://user:pass@localhost/dbname  # For PostgreSQL
   ```

2. **Use production WSGI server**
   ```bash
   pip install gunicorn
   gunicorn backend.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Set up reverse proxy** (nginx example)
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Docker Deployment (Optional)

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN mkdir -p uploads

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 🔍 Design Decisions & Trade-offs

### Embedding Storage
**Decision**: Store embeddings as JSON strings in SQLite
**Pros**: Simple setup, no additional vector database needed
**Cons**: Less efficient than specialized vector databases
**Alternative**: Use Pinecone, Weaviate, or Chroma for production

### Chunking Strategy
**Decision**: Word-based chunking with overlap
**Pros**: Preserves sentence boundaries, maintains context
**Cons**: May split important information across chunks
**Alternative**: Sentence-based or semantic chunking

### Model Selection
**Decision**: Use Hugging Face Inference API
**Pros**: No local GPU requirements, variety of models
**Cons**: API latency, requires internet connection
**Alternative**: Local model deployment with transformers

### Database Choice
**Decision**: SQLite for development, PostgreSQL recommended for production
**Pros**: Easy setup, ACID compliance, relationship management
**Cons**: Not optimized for vector operations
**Alternative**: Vector databases for large-scale deployments

### Frontend Architecture
**Decision**: Vanilla HTML/CSS/JavaScript
**Pros**: Simple, no build process, easy to understand
**Cons**: Limited scalability for complex UIs
**Alternative**: React, Vue, or Angular for larger applications

## 🐛 Troubleshooting

### Common Issues

1. **"HF_API_KEY not provided" error**
   - Ensure you've set the `HF_API_KEY` environment variable
   - Check that your API key is valid and has appropriate permissions

2. **File upload fails**
   - Verify file is a valid Word document (.docx or .doc)
   - Check file size is under the limit (default 10MB)
   - Ensure upload directory exists and is writable

3. **Embedding generation fails**
   - Check internet connection for Hugging Face API
   - Verify API key has sufficient quota
   - Try with smaller text chunks

4. **Chat responses are poor quality**
   - Ensure documents contain relevant information
   - Try adjusting chunk size and overlap parameters
   - Consider using different embedding or LLM models

### Performance Optimization

1. **Slow document processing**
   - Reduce chunk size for faster processing
   - Process documents in smaller batches
   - Consider using local embedding models

2. **High memory usage**
   - Limit concurrent file uploads
   - Implement embedding caching
   - Use streaming for large documents

## 📝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Hugging Face](https://huggingface.co/) for AI model APIs
- [SQLAlchemy](https://www.sqlalchemy.org/) for database ORM
- [python-docx](https://python-docx.readthedocs.io/) for Word document processing