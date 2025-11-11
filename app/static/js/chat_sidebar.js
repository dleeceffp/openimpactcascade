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
                
                // Call onMessageReceived callback
                if (this.config.onMessageReceived) {
                    this.config.onMessageReceived(data.response);
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

// Auto-initialize on DOMContentLoaded if not already initialized
document.addEventListener('DOMContentLoaded', function() {
    if (!ChatSidebar.isInitialized) {
        console.log('[ChatSidebar] Auto-initializing with default config');
        ChatSidebar.init();
    }
});
