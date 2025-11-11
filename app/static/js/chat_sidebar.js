/**
 * Chat Sidebar Component JavaScript
 * Version: v211
 * 
 * Reusable chat functionality for AI assistant sidebar
 * Used across: questionnaire, results, and custom scenario pages
 * 
 * Usage:
 * 1. Include this script in your HTML
 * 2. Call initChatSidebar(config) with your page-specific config
 * 3. Optionally override getContextData() for custom context
 */

// Global chat state
const ChatSidebar = {
    config: null,
    isInitialized: false,
    
    /**
     * Initialize the chat sidebar with page-specific configuration
     * @param {Object} config - Configuration object
     * @param {string} config.apiEndpoint - API endpoint for chat (default: '/api/chat')
     * @param {string} config.pageContext - Page identifier (e.g., 'questionnaire', 'results')
     * @param {Function} config.getContextData - Function to get current page context
     */
    init: function(config = {}) {
        this.config = {
            apiEndpoint: config.apiEndpoint || '/api/chat',
            pageContext: config.pageContext || 'unknown',
            getContextData: config.getContextData || this.defaultGetContextData,
            onMessageSent: config.onMessageSent || null,
            onMessageReceived: config.onMessageReceived || null,
            onError: config.onError || null
        };
        
        this.setupEventListeners();
        this.isInitialized = true;
        console.log('[ChatSidebar] Initialized for page:', this.config.pageContext);
    },
    
    /**
     * Default context data getter (override this per page)
     */
    defaultGetContextData: function() {
        return {
            page: ChatSidebar.config.pageContext,
            timestamp: new Date().toISOString()
        };
    },
    
    /**
     * Setup event listeners for chat interactions
     */
    setupEventListeners: function() {
        // Enter key to send message
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    ChatSidebar.sendMessage();
                }
            });
        }
        
        // Mobile chat toggle
        const mobileToggle = document.getElementById('mobileChatToggle');
        if (mobileToggle) {
            mobileToggle.addEventListener('click', function() {
                ChatSidebar.toggleChat();
            });
        }
        
        // Close button
        const closeBtn = document.getElementById('chatCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', function() {
                ChatSidebar.toggleChat();
            });
        }
    },
    
    /**
     * Send a chat message
     */
    sendMessage: async function() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessageToChat('user', message);
        input.value = '';
        
        // Disable send button
        const sendBtn = document.getElementById('chatSendBtn');
        const originalText = sendBtn.textContent;
        sendBtn.disabled = true;
        sendBtn.textContent = '...';
        
        // Call onMessageSent callback
        if (this.config.onMessageSent) {
            this.config.onMessageSent(message);
        }
        
        try {
            // Get context data
            const context = this.config.getContextData();
            
            // Send to API
            const response = await fetch(this.config.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    context: context
                })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                this.addMessageToChat('assistant', data.response);
                
                // Call onMessageReceived callback with both user message and response
                if (this.config.onMessageReceived) {
                    this.config.onMessageReceived(message, data.response);
                }
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('[ChatSidebar] Error:', error);
            this.addMessageToChat('assistant', 'Sorry, I encountered an error. Please try again.');
            
            // Call onError callback
            if (this.config.onError) {
                this.config.onError(error);
            }
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = originalText;
        }
    },
    
    /**
     * Add a message to the chat display
     * @param {string} role - 'user' or 'assistant'
     * @param {string} content - Message content (can include HTML)
     */
    addMessageToChat: function(role, content) {
        const messagesDiv = document.getElementById('chatMessages');
        if (!messagesDiv) {
            console.error('[ChatSidebar] chatMessages element not found');
            return;
        }
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${role}`;
        
        const label = role === 'user' ? 'You' : 'AI Assistant';
        messageDiv.innerHTML = `
            <div class="message-label">${label}</div>
            <div class="message-bubble">${content}</div>
        `;
        
        messagesDiv.appendChild(messageDiv);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    },
    
    /**
     * Send a quick help question
     * @param {string} question - Pre-defined question to send
     */
    sendQuickHelp: function(question) {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = question;
            this.sendMessage();
        }
    },
    
    /**
     * Toggle chat sidebar visibility (mobile)
     */
    toggleChat: function() {
        const sidebar = document.getElementById('chatSidebar');
        const toggle = document.getElementById('mobileChatToggle');
        
        if (sidebar) {
            sidebar.classList.toggle('open');
        }
        
        // Hide toggle button when chat is open
        if (toggle) {
            toggle.classList.toggle('hidden');
        }
    },
    
    /**
     * Clear all messages from chat
     */
    clearMessages: function() {
        const messagesDiv = document.getElementById('chatMessages');
        if (messagesDiv) {
            // Keep only the welcome message (first child)
            while (messagesDiv.children.length > 1) {
                messagesDiv.removeChild(messagesDiv.lastChild);
            }
        }
    },
    
    /**
     * Export chat history as JSON
     */
    exportChatHistory: function() {
        const messagesDiv = document.getElementById('chatMessages');
        if (!messagesDiv) return null;
        
        const messages = [];
        const messageElements = messagesDiv.querySelectorAll('.chat-message');
        
        messageElements.forEach(el => {
            const role = el.classList.contains('user') ? 'user' : 'assistant';
            const content = el.querySelector('.message-bubble').textContent;
            messages.push({ role, content, timestamp: new Date().toISOString() });
        });
        
        return messages;
    },
    
    /**
     * Save chat history to session storage
     */
    saveChatHistory: function() {
        const history = this.exportChatHistory();
        if (history) {
            sessionStorage.setItem(`chat_history_${this.config.pageContext}`, JSON.stringify(history));
        }
    },
    
    /**
     * Load chat history from session storage
     */
    loadChatHistory: function() {
        const stored = sessionStorage.getItem(`chat_history_${this.config.pageContext}`);
        if (stored) {
            try {
                const history = JSON.parse(stored);
                history.forEach(msg => {
                    if (msg.role !== 'assistant' || history.indexOf(msg) > 0) {
                        // Skip first assistant message (welcome message)
                        this.addMessageToChat(msg.role, msg.content);
                    }
                });
            } catch (e) {
                console.error('[ChatSidebar] Failed to load chat history:', e);
            }
        }
    }
};

// Global functions for backward compatibility and template usage
function initChatSidebar(config) {
    ChatSidebar.init(config);
}

function sendChatMessage() {
    ChatSidebar.sendMessage();
}

function sendQuickHelp(question) {
    ChatSidebar.sendQuickHelp(question);
}

function toggleChat() {
    ChatSidebar.toggleChat();
}

function addMessageToChat(role, content) {
    ChatSidebar.addMessageToChat(role, content);
}

// ========== SESSION-BASED CHAT HISTORY MANAGER ==========

/**
 * ChatHistory - Centralized session-based chat history manager
 * Tracks all chat interactions across pages during the user's session
 * Uses sessionStorage for persistence (no database required for MVP)
 */
const ChatHistory = {
    history: [],
    maxEntries: 100, // Prevent memory issues
    storageKey: 'oic_complete_chat_history',
    
    /**
     * Initialize and load existing history from sessionStorage
     */
    init: function() {
        this.load();
        console.log('[ChatHistory] Initialized with', this.history.length, 'entries');
    },
    
    /**
     * Add a chat exchange to the history
     * @param {string} userMessage - User's message
     * @param {string} assistantResponse - AI assistant's response
     * @param {Object} context - Page context (page, question, assessment data, etc.)
     */
    add: function(userMessage, assistantResponse, context = {}) {
        const entry = {
            timestamp: new Date().toISOString(),
            user: userMessage,
            assistant: assistantResponse,
            context: {
                page: context.page || window.location.pathname,
                ...context
            }
        };
        
        this.history.push(entry);
        
        // Trim if exceeds max entries
        if (this.history.length > this.maxEntries) {
            this.history.shift();
        }
        
        // Persist to sessionStorage
        this.save();
        
        console.log('[ChatHistory] Added entry. Total:', this.history.length);
    },
    
    /**
     * Save history to sessionStorage
     */
    save: function() {
        try {
            sessionStorage.setItem(this.storageKey, JSON.stringify(this.history));
        } catch (e) {
            console.warn('[ChatHistory] Failed to save:', e);
        }
    },
    
    /**
     * Load history from sessionStorage
     */
    load: function() {
        try {
            const saved = sessionStorage.getItem(this.storageKey);
            if (saved) {
                this.history = JSON.parse(saved);
            }
        } catch (e) {
            console.warn('[ChatHistory] Failed to load:', e);
            this.history = [];
        }
    },
    
    /**
     * Get all history entries
     * @returns {Array} Complete chat history
     */
    getAll: function() {
        return this.history;
    },
    
    /**
     * Get history filtered by page
     * @param {string} page - Page identifier or path
     * @returns {Array} Filtered chat history
     */
    getByPage: function(page) {
        return this.history.filter(entry => entry.context.page === page);
    },
    
    /**
     * Get summary statistics
     * @returns {Object} Statistics about chat history
     */
    getStats: function() {
        const pages = {};
        this.history.forEach(entry => {
            const page = entry.context.page;
            pages[page] = (pages[page] || 0) + 1;
        });
        
        return {
            totalExchanges: this.history.length,
            pageBreakdown: pages,
            firstInteraction: this.history.length > 0 ? this.history[0].timestamp : null,
            lastInteraction: this.history.length > 0 ? this.history[this.history.length - 1].timestamp : null
        };
    },
    
    /**
     * Export history as formatted text
     * @param {boolean} includeContext - Include context data in export
     * @returns {string} Formatted text export
     */
    exportAsText: function(includeContext = true) {
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        const stats = this.getStats();
        
        let content = `OpenImpactCascade - Complete Chat History\n`;
        content += `Generated: ${new Date().toLocaleString()}\n`;
        content += `Total Exchanges: ${stats.totalExchanges}\n`;
        content += `Session Duration: ${stats.firstInteraction ? new Date(stats.firstInteraction).toLocaleString() : 'N/A'} to ${stats.lastInteraction ? new Date(stats.lastInteraction).toLocaleString() : 'N/A'}\n`;
        content += `\nPage Breakdown:\n`;
        Object.entries(stats.pageBreakdown).forEach(([page, count]) => {
            content += `  - ${page}: ${count} exchanges\n`;
        });
        content += `\n${'='.repeat(80)}\n\n`;
        
        this.history.forEach((entry, index) => {
            content += `[${index + 1}] ${new Date(entry.timestamp).toLocaleString()}\n`;
            content += `Page: ${entry.context.page}\n`;
            
            if (includeContext && Object.keys(entry.context).length > 1) {
                content += `Context:\n`;
                Object.entries(entry.context).forEach(([key, value]) => {
                    if (key !== 'page') {
                        content += `  ${key}: ${JSON.stringify(value)}\n`;
                    }
                });
            }
            
            content += `\nYOU:\n${entry.user}\n\n`;
            content += `ASSISTANT:\n${entry.assistant}\n\n`;
            content += `${'-'.repeat(80)}\n\n`;
        });
        
        return content;
    },
    
    /**
     * Export history as JSON
     * @returns {string} JSON string of complete history
     */
    exportAsJSON: function() {
        return JSON.stringify({
            exported: new Date().toISOString(),
            version: 'v2-rag-enhanced',
            statistics: this.getStats(),
            history: this.history
        }, null, 2);
    },
    
    /**
     * Clear all history
     */
    clear: function() {
        this.history = [];
        sessionStorage.removeItem(this.storageKey);
        console.log('[ChatHistory] Cleared');
    },
    
    /**
     * Check if this is a new session (e.g., user returned to home page)
     * Can be used to automatically clear history on session start
     */
    isNewSession: function() {
        // Check if there's a session marker
        const sessionMarker = sessionStorage.getItem('oic_session_active');
        return !sessionMarker;
    },
    
    /**
     * Mark session as active (call when user starts an assessment)
     */
    markSessionActive: function() {
        sessionStorage.setItem('oic_session_active', 'true');
        console.log('[ChatHistory] Session marked as active');
    },
    
    /**
     * Clear session marker (call when user returns to home)
     */
    clearSessionMarker: function() {
        sessionStorage.removeItem('oic_session_active');
        console.log('[ChatHistory] Session marker cleared');
    },
    
    /**
     * Import existing chat messages from a page's local chatHistory array
     * Call this on page load to capture pre-existing conversations
     * @param {Array} localHistory - Array of {user, assistant} objects
     * @param {Object} context - Page context to apply to all entries
     */
    importFromLocal: function(localHistory, context = {}) {
        if (!Array.isArray(localHistory) || localHistory.length === 0) {
            return;
        }
        
        let importedCount = 0;
        localHistory.forEach(exchange => {
            if (exchange.user && exchange.assistant) {
                // Check if this exchange already exists (avoid duplicates)
                const isDuplicate = this.history.some(entry => 
                    entry.user === exchange.user && 
                    entry.assistant === exchange.assistant &&
                    entry.context.page === (context.page || window.location.pathname)
                );
                
                if (!isDuplicate) {
                    this.add(exchange.user, exchange.assistant, context);
                    importedCount++;
                }
            }
        });
        
        console.log('[ChatHistory] Imported', importedCount, 'new entries from local history (', localHistory.length - importedCount, 'duplicates skipped)');
    }
};

// Initialize ChatHistory on load
ChatHistory.init();

// ========== GLOBAL EXPORT FUNCTIONS ==========

/**
 * Export complete chat history as text file
 */
function exportCompleteHistory() {
    const allHistory = ChatHistory.getAll();
    
    if (allHistory.length === 0) {
        alert('No chat history to export. Start a conversation first!');
        return;
    }
    
    // Debug: Log what we're about to export
    console.log('[ChatHistory] Exporting', allHistory.length, 'entries');
    console.log('[ChatHistory] Page breakdown:', ChatHistory.getStats().pageBreakdown);
    
    const content = ChatHistory.exportAsText(true);
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `oic-complete-chat-history-${timestamp}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log('[ChatHistory] Exported as text');
    
    // Show confirmation with stats
    const stats = ChatHistory.getStats();
    alert(`Exported ${stats.totalExchanges} chat exchanges!\n\nPage breakdown:\n${Object.entries(stats.pageBreakdown).map(([page, count]) => `  ${page}: ${count}`).join('\n')}`);
}

/**
 * Export complete chat history as JSON file
 */
function exportHistoryAsJSON() {
    if (ChatHistory.getAll().length === 0) {
        alert('No chat history to export. Start a conversation first!');
        return;
    }
    
    const content = ChatHistory.exportAsJSON();
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `oic-chat-history-${timestamp}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    console.log('[ChatHistory] Exported as JSON');
}

/**
 * Get chat history statistics
 * @returns {Object} Statistics object
 */
function getChatStats() {
    return ChatHistory.getStats();
}

/**
 * Clear complete chat history
 */
function clearChatHistory() {
    if (confirm('Are you sure you want to clear all chat history? This cannot be undone.')) {
        ChatHistory.clear();
        alert('Chat history cleared!');
    }
}

/**
 * Debug: View complete chat history in console
 */
function viewChatHistory() {
    const history = ChatHistory.getAll();
    const stats = ChatHistory.getStats();
    
    console.log('=== COMPLETE CHAT HISTORY ===');
    console.log('Total Exchanges:', stats.totalExchanges);
    console.log('Page Breakdown:', stats.pageBreakdown);
    console.log('First Interaction:', stats.firstInteraction);
    console.log('Last Interaction:', stats.lastInteraction);
    console.log('\n=== ALL ENTRIES ===');
    
    history.forEach((entry, index) => {
        console.log(`\n[${index + 1}] ${entry.timestamp}`);
        console.log(`Page: ${entry.context.page}`);
        console.log(`User: ${entry.user}`);
        console.log(`Assistant: ${entry.assistant.substring(0, 100)}${entry.assistant.length > 100 ? '...' : ''}`);
    });
    
    console.log('\n=== END OF HISTORY ===');
    return history;
}

// Auto-initialize on DOMContentLoaded if not already initialized
document.addEventListener('DOMContentLoaded', function() {
    if (!ChatSidebar.isInitialized) {
        console.log('[ChatSidebar] Auto-initializing with default config');
        ChatSidebar.init();
    }
});
