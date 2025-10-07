#!/usr/bin/env python3
"""
Document RAG Chatbot - Simple entry point for Windows

This script starts the FastAPI application without reload mode.
"""

import os
import sys
import uvicorn
from backend.config import settings

def main():
    """Main entry point for the application."""
    print("🚀 Starting Document RAG Chatbot...")
    print(f"📍 Server will run on http://{settings.API_HOST}:{settings.API_PORT}")
    print(f"📁 Upload directory: {settings.UPLOAD_DIR}")
    print(f"🤖 HF API configured: {'✅' if settings.HF_API_KEY else '❌'}")
    
    if not settings.HF_API_KEY:
        print("\n⚠️  WARNING: HF_API_KEY not set!")
        print("   Please set your Hugging Face API key in the .env file")
        print("   Get your API key from: https://huggingface.co/settings/tokens")
    
    # Create upload directory if it doesn't exist
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # Start the server without reload (better for Windows)
    uvicorn.run(
        "backend.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=False,  # Disabled for Windows compatibility
        log_level="info"
    )

if __name__ == "__main__":
    main()