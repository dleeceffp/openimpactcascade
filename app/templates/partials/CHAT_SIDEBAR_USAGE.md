# Chat Sidebar Component Usage Guide

## Overview
The chat sidebar is a reusable component for the AI assistant that can be included in any page.

## Files
- `partials/chat_sidebar.html` - HTML template
- `static/css/chat_sidebar.css` - Styles
- `static/js/chat_sidebar.js` - JavaScript functionality

## Basic Usage

### 1. Include CSS and JS in your template

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/chat_sidebar.css') }}">
<script src="{{ url_for('static', filename='js/chat_sidebar.js') }}"></script>
```

### 2. Configure the chat sidebar

```html
{% set chat_config = {
    'welcome_message': 'Your welcome message here',
    'quick_help_buttons': [
        {'text': '📝 Button 1', 'question': 'What is this?'},
        {'text': '💡 Button 2', 'question': 'How does this work?'}
    ],
    'page_context': 'your_page_name'
} %}
```

### 3. Include the sidebar

```html
{% include 'partials/chat_sidebar.html' %}
```

### 4. Initialize JavaScript (in your page's script section)

```javascript
<script>
    // Initialize chat with custom configuration
    initChatSidebar({
        apiEndpoint: '/api/chat',  // Your chat API endpoint
        pageContext: 'your_page_name',
        getContextData: function() {
            // Return page-specific context
            return {
                page: 'your_page_name',
                industry: document.getElementById('industry')?.value,
                region: document.getElementById('region')?.value,
                // Add any other context your page needs
            };
        }
    });
</script>
```

## Advanced Configuration

### Custom Context Data

Override `getContextData` to provide page-specific context:

```javascript
initChatSidebar({
    pageContext: 'results',
    getContextData: function() {
        return {
            page: 'results',
            risk_scenario: '{{ risk_scenario }}',
            expected_loss: {{ expected_loss }},
            p90_loss: {{ p90_loss }},
            // Include any Jinja2 variables or DOM values
        };
    }
});
```

### Callbacks

```javascript
initChatSidebar({
    pageContext: 'questionnaire',
    onMessageSent: function(message) {
        console.log('User sent:', message);
        // Track analytics, etc.
    },
    onMessageReceived: function(response) {
        console.log('AI responded:', response);
        // Update UI, etc.
    },
    onError: function(error) {
        console.error('Chat error:', error);
        // Show custom error message
    }
});
```

## Layout Considerations

### Add margin to main content

The chat sidebar is 400px wide and fixed to the right. Add margin to your main content:

```css
.main-content {
    margin-right: 400px;
}

@media (max-width: 1024px) {
    .main-content {
        margin-right: 0; /* Chat becomes overlay on mobile */
    }
}
```

### Page wrapper

```html
<div class="page-wrapper">
    <div class="main-content">
        <!-- Your page content -->
    </div>
    {% include 'partials/chat_sidebar.html' %}
</div>
```

## Example: Questionnaire Page

```html
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/chat_sidebar.css') }}">
</head>
<body>
    {% set chat_config = {
        'welcome_message': '👋 Hi! I can help you with this questionnaire.',
        'quick_help_buttons': [
            {'text': '📝 Explain Question', 'question': 'Explain this question'},
            {'text': '💡 Examples', 'question': 'Give me examples'}
        ],
        'page_context': 'questionnaire'
    } %}
    
    <div class="page-wrapper">
        <div class="main-content">
            <h1>Questionnaire</h1>
            <!-- Your content -->
        </div>
        {% include 'partials/chat_sidebar.html' %}
    </div>
    
    <script src="{{ url_for('static', filename='js/chat_sidebar.js') }}"></script>
    <script>
        initChatSidebar({
            pageContext: 'questionnaire',
            getContextData: function() {
                return {
                    page: 'questionnaire',
                    question_text: '{{ current_question }}',
                    industry: '{{ industry }}',
                    region: '{{ region }}'
                };
            }
        });
    </script>
</body>
</html>
```

## API Endpoint

The chat sidebar expects a POST endpoint at `/api/chat` (configurable) that accepts:

```json
{
    "message": "User's message",
    "context": {
        "page": "page_name",
        "...": "other context"
    }
}
```

And returns:

```json
{
    "status": "success",
    "response": "AI's response"
}
```

## Mobile Behavior

- Desktop (>1024px): Sidebar is always visible
- Mobile (≤1024px): Sidebar slides in from right, toggle button appears
- Close button appears on mobile
- Smooth transitions

## Utility Functions

```javascript
// Clear chat history
ChatSidebar.clearMessages();

// Export chat history
const history = ChatSidebar.exportChatHistory();

// Save to session storage
ChatSidebar.saveChatHistory();

// Load from session storage
ChatSidebar.loadChatHistory();

// Add custom message
ChatSidebar.addMessageToChat('assistant', 'Custom message');
```

## Migration from Old Code

### Before (inline code):
```html
<div class="chat-sidebar">
    <!-- 100+ lines of HTML -->
</div>
<script>
    // 200+ lines of JavaScript
</script>
<style>
    /* 300+ lines of CSS */
</style>
```

### After (component):
```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/chat_sidebar.css') }}">
{% include 'partials/chat_sidebar.html' %}
<script src="{{ url_for('static', filename='js/chat_sidebar.js') }}"></script>
<script>
    initChatSidebar({ pageContext: 'my_page' });
</script>
```

## Benefits

✅ **DRY**: Write once, use everywhere  
✅ **Maintainable**: Update in one place  
✅ **Consistent**: Same UX across all pages  
✅ **Flexible**: Easy to customize per page  
✅ **Testable**: Isolated component logic  
✅ **Smaller files**: Reduced template bloat
