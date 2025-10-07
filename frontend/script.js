// Global state
let currentSessionId = null;
let currentFileId = null;
let isLoading = false;

// DOM elements
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const uploadStatus = document.getElementById('uploadStatus');
const filesList = document.getElementById('filesList');
const chatSection = document.getElementById('chatSection');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const currentFileName = document.getElementById('currentFileName');
const newChatBtn = document.getElementById('newChatBtn');
const sessionsList = document.getElementById('sessionsList');
const loadingModal = document.getElementById('loadingModal');
const loadingText = document.getElementById('loadingText');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
    loadFiles();
    loadSessions();
    checkAPIHealth();
});

// Event listeners
function setupEventListeners() {
    // File upload
    fileInput.addEventListener('change', handleFileSelect);
    uploadArea.addEventListener('click', () => fileInput.click());
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    
    // Chat
    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    sendBtn.addEventListener('click', sendMessage);
    newChatBtn.addEventListener('click', startNewChat);
}

// File upload handlers
function handleFileSelect(event) {
    const files = Array.from(event.target.files);
    uploadFiles(files);
}

function handleDragOver(event) {
    event.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(event) {
    event.preventDefault();
    uploadArea.classList.remove('dragover');
    const files = Array.from(event.dataTransfer.files);
    uploadFiles(files);
}

// Upload files
async function uploadFiles(files) {
    if (files.length === 0) return;
    
    // Validate files
    const validFiles = files.filter(file => {
        const isValid = file.name.toLowerCase().endsWith('.docx') || file.name.toLowerCase().endsWith('.doc');
        if (!isValid) {
            showStatus(`${file.name}: Only Word documents (.docx, .doc) are supported`, 'error');
        }
        return isValid;
    });
    
    if (validFiles.length === 0) return;
    
    showLoading('Uploading and processing documents...');
    
    const formData = new FormData();
    validFiles.forEach(file => {
        formData.append('files', file);
    });
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        // Show results
        uploadStatus.innerHTML = '';
        
        if (result.uploaded_files && result.uploaded_files.length > 0) {
            result.uploaded_files.forEach(file => {
                showStatus(`✅ ${file.filename} uploaded successfully (${file.chunks_count} chunks)`, 'success');
            });
        }
        
        if (result.errors && result.errors.length > 0) {
            result.errors.forEach(error => {
                showStatus(`❌ ${error}`, 'error');
            });
        }
        
        // Refresh files list
        await loadFiles();
        
    } catch (error) {
        console.error('Upload error:', error);
        showStatus('❌ Upload failed. Please try again.', 'error');
    } finally {
        hideLoading();
        fileInput.value = '';
    }
}

// Load files list
async function loadFiles() {
    try {
        const response = await fetch('/api/files');
        const files = await response.json();
        
        if (files.length === 0) {
            filesList.innerHTML = '<p class="no-files">No documents uploaded yet</p>';
            return;
        }
        
        filesList.innerHTML = files.map(file => `
            <div class="file-item">
                <div class="file-info">
                    <h4>📄 ${file.original_filename}</h4>
                    <p>Uploaded: ${new Date(file.upload_timestamp).toLocaleString()}</p>
                    <p>Text length: ${file.text_length.toLocaleString()} characters</p>
                </div>
                <div class="file-actions">
                    <button class="btn-small btn-chat" onclick="startChatWithFile(${file.id}, '${file.original_filename}')">
                        💬 Chat
                    </button>
                    <button class="btn-small btn-delete" onclick="deleteFile(${file.id})">
                        🗑️ Delete
                    </button>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading files:', error);
        filesList.innerHTML = '<p class="no-files">Error loading files</p>';
    }
}

// Start chat with file
async function startChatWithFile(fileId, filename) {
    showLoading('Starting chat session...');
    
    try {
        const formData = new FormData();
        formData.append('file_id', fileId);
        
        const response = await fetch('/api/chat/start', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        currentSessionId = result.session_id;
        currentFileId = fileId;
        currentFileName.textContent = filename;
        
        // Clear chat and show section
        chatMessages.innerHTML = `
            <div class="welcome-message">
                <p>👋 Hi! I'm ready to answer questions about "${filename}".</p>
                <p>Ask me anything about the content!</p>
            </div>
        `;
        
        chatSection.style.display = 'block';
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.focus();
        
        // Refresh sessions
        await loadSessions();
        
    } catch (error) {
        console.error('Error starting chat:', error);
        alert('Failed to start chat session. Please try again.');
    } finally {
        hideLoading();
    }
}

// Send message
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message || !currentSessionId || isLoading) return;
    
    // Add user message to chat
    addMessageToChat('user', message);
    messageInput.value = '';
    messageInput.disabled = true;
    sendBtn.disabled = true;
    isLoading = true;
    
    // Add loading indicator
    const loadingId = addMessageToChat('assistant', '🤔 Thinking...');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                session_id: currentSessionId,
                message: message
            })
        });
        
        const result = await response.json();
        
        // Remove loading message and add response
        document.getElementById(loadingId).remove();
        addMessageToChat('assistant', result.response);
        
    } catch (error) {
        console.error('Error sending message:', error);
        document.getElementById(loadingId).remove();
        addMessageToChat('assistant', '❌ Sorry, I encountered an error. Please try again.');
    } finally {
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.focus();
        isLoading = false;
    }
}

// Add message to chat
function addMessageToChat(type, content) {
    const messageId = 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    const avatar = type === 'user' ? '👤' : '🤖';
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${type}`;
    messageElement.id = messageId;
    messageElement.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">${content}</div>
    `;
    
    // Remove welcome message if it exists
    const welcomeMessage = chatMessages.querySelector('.welcome-message');
    if (welcomeMessage) {
        welcomeMessage.remove();
    }
    
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Start new chat
function startNewChat() {
    if (currentFileId) {
        startChatWithFile(currentFileId, currentFileName.textContent);
    }
}

// Load chat sessions
async function loadSessions() {
    try {
        const response = await fetch('/api/sessions');
        const sessions = await response.json();
        
        if (sessions.length === 0) {
            sessionsList.innerHTML = '<p class="no-sessions">No chat sessions yet</p>';
            return;
        }
        
        sessionsList.innerHTML = sessions.map(session => `
            <div class="session-item" onclick="loadChatHistory('${session.session_id}', '${session.filename}')">
                <h4>💬 ${session.filename}</h4>
                <p>Started: ${new Date(session.created_at).toLocaleString()}</p>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading sessions:', error);
        sessionsList.innerHTML = '<p class="no-sessions">Error loading sessions</p>';
    }
}

// Load chat history
async function loadChatHistory(sessionId, filename) {
    showLoading('Loading chat history...');
    
    try {
        const response = await fetch(`/api/chat/${sessionId}/history`);
        const messages = await response.json();
        
        currentSessionId = sessionId;
        currentFileName.textContent = filename;
        
        // Clear and populate chat
        chatMessages.innerHTML = '';
        
        if (messages.length === 0) {
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    <p>👋 Chat history loaded for "${filename}".</p>
                    <p>Continue the conversation!</p>
                </div>
            `;
        } else {
            messages.forEach(msg => {
                addMessageToChat(msg.message_type, msg.content);
            });
        }
        
        chatSection.style.display = 'block';
        messageInput.disabled = false;
        sendBtn.disabled = false;
        messageInput.focus();
        
    } catch (error) {
        console.error('Error loading chat history:', error);
        alert('Failed to load chat history.');
    } finally {
        hideLoading();
    }
}

// Delete file
async function deleteFile(fileId) {
    if (!confirm('Are you sure you want to delete this file? This will also delete all associated chat sessions.')) {
        return;
    }
    
    showLoading('Deleting file...');
    
    try {
        const response = await fetch(`/api/files/${fileId}`, {
            method: 'DELETE'
        });
        
        if (response.ok) {
            showStatus('✅ File deleted successfully', 'success');
            
            // If this was the current chat file, hide chat section
            if (currentFileId === fileId) {
                chatSection.style.display = 'none';
                currentSessionId = null;
                currentFileId = null;
            }
            
            // Refresh lists
            await loadFiles();
            await loadSessions();
        } else {
            throw new Error('Delete failed');
        }
        
    } catch (error) {
        console.error('Error deleting file:', error);
        showStatus('❌ Failed to delete file', 'error');
    } finally {
        hideLoading();
    }
}

// Check API health
async function checkAPIHealth() {
    try {
        const response = await fetch('/api/health');
        const health = await response.json();
        
        if (!health.hf_api_configured) {
            showStatus('⚠️ Warning: Hugging Face API key not configured. Please set HF_API_KEY environment variable.', 'error');
        }
        
    } catch (error) {
        console.error('Health check failed:', error);
        showStatus('❌ API connection failed', 'error');
    }
}

// Utility functions
function showStatus(message, type) {
    const statusElement = document.createElement('div');
    statusElement.className = `status-item status-${type}`;
    statusElement.textContent = message;
    uploadStatus.appendChild(statusElement);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (statusElement.parentNode) {
            statusElement.parentNode.removeChild(statusElement);
        }
    }, 5000);
}

function showLoading(message) {
    loadingText.textContent = message;
    loadingModal.style.display = 'block';
}

function hideLoading() {
    loadingModal.style.display = 'none';
}