/**
 * LOCAL RAG SYSTEM - JAVASCRIPT APPLICATION
 * Handles all frontend interactions and API communication
 */

class RAGApp {
    constructor() {
        this.API_BASE = '/api'; // Backend API endpoint
        this.documents = [];
        this.isSystemReady = false;
        this.currentConversation = [];
        
        this.init();
    }

    /**
     * Initialize the application
     */
    init() {
        this.initializeElements();
        this.attachEventListeners();
        this.checkSystemStatus();
        this.loadDocuments();
        
        // Auto-resize textarea
        this.setupTextareaAutoResize();
    }

    /**
     * Get DOM elements
     */
    initializeElements() {
        // Status
        this.statusIndicator = document.getElementById('statusIndicator');
        
        // Sidebar
        this.docCount = document.getElementById('docCount');
        this.uploadBtn = document.getElementById('uploadBtn');
        this.refreshBtn = document.getElementById('refreshBtn');
        this.documentsList = document.getElementById('documentsList');
        this.chunksCount = document.getElementById('chunksCount');
        this.embeddingsCount = document.getElementById('embeddingsCount');
        
        // Chat
        this.welcomeScreen = document.getElementById('welcomeScreen');
        this.chatMessages = document.getElementById('chatMessages');
        this.userInput = document.getElementById('userInput');
        this.sendBtn = document.getElementById('sendBtn');
        
        // Loading
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        
        // Toast
        this.toastContainer = document.getElementById('toastContainer');
    }

    /**
     * Attach event listeners
     */
    attachEventListeners() {
        // Upload button
        this.uploadBtn.addEventListener('click', () => this.handleUpload());
        
        // Refresh button
        this.refreshBtn.addEventListener('click', () => this.refreshDatabase());
        
        // Send button
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        
        // Input handling
        this.userInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        this.userInput.addEventListener('input', () => {
            this.sendBtn.disabled = !this.userInput.value.trim() || !this.isSystemReady;
        });
    }

    /**
     * Setup textarea auto-resize
     */
    setupTextareaAutoResize() {
        this.userInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }

    /**
     * Check system status
     */
    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.API_BASE}/status`);
            const data = await response.json();
            
            if (data.status === 'ready') {
                this.updateSystemStatus('ready', 'System Ready');
                this.isSystemReady = true;
                this.sendBtn.disabled = false;
            } else {
                this.updateSystemStatus('initializing', data.message || 'Initializing...');
                // Retry after 2 seconds
                setTimeout(() => this.checkSystemStatus(), 2000);
            }
        } catch (error) {
            console.error('Status check error:', error);
            this.updateSystemStatus('error', 'Connection Error');
            this.showToast('Unable to connect to backend server', 'error');
        }
    }

    /**
     * Update system status indicator
     */
    updateSystemStatus(status, message) {
        const statusClasses = {
            'ready': 'ready',
            'error': 'error',
            'initializing': ''
        };
        
        this.statusIndicator.className = 'status-indicator ' + (statusClasses[status] || '');
        this.statusIndicator.querySelector('.status-text').textContent = message;
    }

    /**
     * Load documents from backend
     */
    async loadDocuments() {
        try {
            const response = await fetch(`${this.API_BASE}/documents`);
            const data = await response.json();
            
            this.documents = data.documents || [];
            this.updateDocumentsList();
            this.updateStats(data.stats);
        } catch (error) {
            console.error('Load documents error:', error);
            this.updateStats({ chunks: 0, embeddings: 0 });
        }
    }

    /**
     * Update documents list UI
     */
    updateDocumentsList() {
        this.docCount.textContent = `${this.documents.length} Document${this.documents.length !== 1 ? 's' : ''}`;
        
        if (this.documents.length === 0) {
            this.documentsList.innerHTML = `
                <div class="empty-state">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                        <polyline points="14 2 14 8 20 8"></polyline>
                        <line x1="12" y1="18" x2="12" y2="12"></line>
                        <line x1="9" y1="15" x2="15" y2="15"></line>
                    </svg>
                    <p>No documents yet</p>
                    <span>Upload PDFs or text files to get started</span>
                </div>
            `;
        } else {
            this.documentsList.innerHTML = this.documents.map(doc => this.createDocumentItem(doc)).join('');
        }
    }

    /**
     * Create document item HTML
     */
    createDocumentItem(doc) {
        const icon = doc.type === 'pdf' ? '📕' : '📄';
        const size = this.formatFileSize(doc.size);
        
        return `
            <div class="document-item" data-id="${doc.id}">
                <div class="document-icon">${icon}</div>
                <div class="document-name">${this.escapeHtml(doc.name)}</div>
                <div class="document-meta">
                    <span>${size}</span>
                    <span>${doc.type.toUpperCase()}</span>
                </div>
            </div>
        `;
    }

    /**
     * Update statistics
     */
    updateStats(stats) {
        // Handle explicit 0 values correctly
        const chunks = (stats && stats.chunks !== undefined) ? stats.chunks : 0;
        const embeddings = (stats && stats.embeddings !== undefined) ? stats.embeddings : 0;
        
        this.chunksCount.textContent = chunks.toLocaleString();
        this.embeddingsCount.textContent = embeddings.toLocaleString();
    }

    /**
     * Handle file upload
     */
    async handleUpload() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.pdf,.txt,.docx,.pptx,.csv,.xlsx,.png,.jpg'; // Updated extensions
        input.multiple = true;
        
        input.onchange = async (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;
            
            this.showLoading('Uploading and processing documents...');
            
            try {
                const formData = new FormData();
                files.forEach(file => formData.append('files', file));
                
                const response = await fetch(`${this.API_BASE}/upload`, {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    this.showToast(`Successfully uploaded ${files.length} file(s)`, 'success');
                    await this.loadDocuments();
                } else {
                    throw new Error(data.message || 'Upload failed');
                }
            } catch (error) {
                console.error('Upload error:', error);
                this.showToast('Upload failed', 'error');
            } finally {
                this.hideLoading();
            }
        };
        
        input.click();
    }

    /**
     * Refresh database
     */
    async refreshDatabase() {
        this.showLoading('Rebuilding Knowledge Base (This may take a while)...');
        
        try {
            const response = await fetch(`${this.API_BASE}/refresh`, {
                method: 'POST'
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showToast('Database refreshed successfully', 'success');
                await this.loadDocuments();
            } else {
                throw new Error(data.message || 'Refresh failed');
            }
        } catch (error) {
            console.error('Refresh error:', error);
            this.showToast('Refresh failed', 'error');
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Send message to RAG system
     */
    async sendMessage() {
        const message = this.userInput.value.trim();
        if (!message || !this.isSystemReady) return;
        
        // Hide welcome screen on first message
        if (this.welcomeScreen.style.display !== 'none') {
            this.welcomeScreen.style.display = 'none';
            this.chatMessages.style.display = 'flex';
        }
        
        // Add user message to UI
        this.addMessage('user', message);
        
        // Clear input
        this.userInput.value = '';
        this.userInput.style.height = 'auto';
        this.sendBtn.disabled = true;
        
        // Show typing indicator
        const typingId = this.addTypingIndicator();
        
        try {
            const response = await fetch(`${this.API_BASE}/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ query: message })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator(typingId);
            
            if (data.success) {
                this.addMessage('assistant', data.answer, data.sources);
            } else {
                throw new Error(data.message || 'Query failed');
            }
        } catch (error) {
            console.error('Query error:', error);
            this.removeTypingIndicator(typingId);
            this.addMessage('assistant', 'Sorry, I encountered an error while processing your request.');
        }
    }

    /**
     * Add message to chat (Fixed for Rich Sources)
     */
    addMessage(role, content, sources = []) {
        const timestamp = new Date().toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
        
        const avatar = role === 'user' ? '👤' : '🤖';
        
        // --- NEW: Rich Source Rendering ---
        let sourcesHtml = '';
        if (sources && sources.length > 0) {
            sourcesHtml = `
                <div class="message-sources">
                    <div class="sources-title">📚 Sources & Traceability</div>
                    ${sources.map(src => {
                        // Extract properties safely
                        const fileName = this.escapeHtml(src.source || 'Unknown');
                        const pageNum = src.page !== 'N/A' ? `<span class="meta-tag">Page ${src.page}</span>` : '';
                        
                        // Traceability Data
                        let traceInfo = '';
                        if (src.traceability && src.traceability.upload_date) {
                            const dateStr = src.traceability.upload_date.split(' ')[0];
                            traceInfo = `<span class="meta-tag">📅 ${dateStr}</span>`;
                        }

                        // Links (REQ-xxx)
                        let linksHtml = '';
                        if (src.links && src.links.length > 0) {
                            linksHtml = `<div class="source-links">🔗 ${src.links}</div>`;
                        }
                        
                        return `
                        <div class="source-item">
                            <div class="source-header">
                                <span class="file-name">📄 ${fileName}</span>
                                <div class="source-meta">
                                    ${pageNum}
                                    ${traceInfo}
                                </div>
                            </div>
                            ${linksHtml}
                        </div>`;
                    }).join('')}
                </div>
            `;
        }
        
        const messageHtml = `
            <div class="message ${role}">
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    <div class="message-text">${this.formatMessageContent(content)}</div>
                    ${sourcesHtml}
                    <div class="message-timestamp">${timestamp}</div>
                </div>
            </div>
        `;
        
        this.chatMessages.insertAdjacentHTML('beforeend', messageHtml);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }

    /**
     * Add typing indicator
     */
    addTypingIndicator() {
        const id = 'typing-' + Date.now();
        const html = `
            <div class="message assistant" id="${id}">
                <div class="message-avatar">🤖</div>
                <div class="message-content">
                    <div class="typing-indicator">
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                        <div class="typing-dot"></div>
                    </div>
                </div>
            </div>
        `;
        
        this.chatMessages.insertAdjacentHTML('beforeend', html);
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        
        return id;
    }

    /**
     * Remove typing indicator
     */
    removeTypingIndicator(id) {
        const element = document.getElementById(id);
        if (element) {
            element.remove();
        }
    }

    /**
     * Format message content (basic markdown-like formatting)
     */
    formatMessageContent(content) {
        let formatted = this.escapeHtml(content);
        
        // Code blocks
        formatted = formatted.replace(/```(\w+)?\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
        
        // Inline code
        formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');
        
        // Bold
        formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Line breaks
        formatted = formatted.replace(/\n/g, '<br>');
        
        return formatted;
    }

    /**
     * Show loading overlay
     */
    showLoading(text = 'Processing...') {
        this.loadingText.textContent = text;
        this.loadingOverlay.style.display = 'flex';
    }

    /**
     * Hide loading overlay
     */
    hideLoading() {
        this.loadingOverlay.style.display = 'none';
    }

    /**
     * Show toast notification
     */
    showToast(message, type = 'info') {
        const icons = {
            'success': '✓',
            'error': '✕',
            'info': 'ℹ'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${icons[type]}</div>
            <div class="toast-message">${this.escapeHtml(message)}</div>
        `;
        
        this.toastContainer.appendChild(toast);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 4000);
    }

    /**
     * Utility: Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Utility: Escape HTML
     */
    escapeHtml(text) {
        if (typeof text !== 'string') return String(text); // Safety check
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.ragApp = new RAGApp();
});