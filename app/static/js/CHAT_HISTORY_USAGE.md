# Chat History Manager - Usage Guide

## Overview

The `ChatHistory` module provides session-based chat history tracking across all pages in the OpenImpactCascade application. It uses `sessionStorage` for persistence during the user's session without requiring a database.

## Features

✅ **Session Persistence** - History survives page navigation  
✅ **Automatic Tracking** - Integrated with all three chat pages  
✅ **Context-Rich** - Captures page, question, and assessment context  
✅ **Multiple Export Formats** - Text and JSON exports  
✅ **Statistics** - Summary stats about chat interactions  
✅ **Memory Safe** - Limits to 100 entries to prevent issues  

## Integration Status

All three pages are integrated with ChatHistory:

1. **`generate_custom.html`** - Custom scenario generation
2. **`questionnaire_chat_rationale.html`** - Questionnaire assistance
3. **`results.html`** - Risk reduction recommendations

## API Reference

### Adding to History

```javascript
ChatHistory.add(userMessage, assistantResponse, context);
```

**Parameters:**
- `userMessage` (string): The user's question/message
- `assistantResponse` (string): The AI assistant's response
- `context` (object): Page-specific context data

**Example:**
```javascript
ChatHistory.add(
    "How can I reduce likelihood?",
    "You can reduce likelihood by implementing preventive controls...",
    {
        page: 'results',
        industry: 'Financial Services',
        region: 'North America',
        expected_loss: 125000,
        p90_loss: 450000
    }
);
```

### Retrieving History

```javascript
// Get all history
const allHistory = ChatHistory.getAll();

// Get history for specific page
const resultsHistory = ChatHistory.getByPage('results');

// Get statistics
const stats = ChatHistory.getStats();
// Returns: { totalExchanges, pageBreakdown, firstInteraction, lastInteraction }
```

### Exporting History

```javascript
// Export as formatted text file
exportCompleteHistory();

// Export as JSON file
exportHistoryAsJSON();

// Get stats programmatically
const stats = getChatStats();
console.log(`Total exchanges: ${stats.totalExchanges}`);
```

### Clearing History

```javascript
// Clear all history (with confirmation)
clearChatHistory();

// Clear programmatically
ChatHistory.clear();
```

## Export Format Examples

### Text Export

```
OpenImpactCascade - Complete Chat History
Generated: 11/11/2025, 12:00:00 PM
Total Exchanges: 15
Session Duration: 11/11/2025, 11:30:00 AM to 11/11/2025, 12:00:00 PM

Page Breakdown:
  - custom_scenario_generation: 3 exchanges
  - questionnaire: 8 exchanges
  - results: 4 exchanges

================================================================================

[1] 11/11/2025, 11:30:15 AM
Page: custom_scenario_generation
Context:
  industry: "Financial Services"
  region: "North America"

YOU:
What makes a good risk scenario?

ASSISTANT:
A good risk scenario should be specific, measurable, and focused on a single threat...

--------------------------------------------------------------------------------
```

### JSON Export

```json
{
  "exported": "2025-11-11T19:00:00.000Z",
  "version": "v2-rag-enhanced",
  "statistics": {
    "totalExchanges": 15,
    "pageBreakdown": {
      "custom_scenario_generation": 3,
      "questionnaire": 8,
      "results": 4
    },
    "firstInteraction": "2025-11-11T18:30:00.000Z",
    "lastInteraction": "2025-11-11T19:00:00.000Z"
  },
  "history": [
    {
      "timestamp": "2025-11-11T18:30:15.000Z",
      "user": "What makes a good risk scenario?",
      "assistant": "A good risk scenario should be specific...",
      "context": {
        "page": "custom_scenario_generation",
        "industry": "Financial Services",
        "region": "North America"
      }
    }
  ]
}
```

## Use Cases

### 1. Session Report Generation

Export complete chat history at the end of an assessment session:

```javascript
// Add export button to results page
<button onclick="exportCompleteHistory()">
    📋 Export Complete Session Report
</button>
```

### 2. Analytics & Insights

Analyze user behavior and common questions:

```javascript
const stats = getChatStats();
console.log('Most active page:', 
    Object.entries(stats.pageBreakdown)
        .sort((a, b) => b[1] - a[1])[0][0]
);
```

### 3. Quality Assurance

Review chat interactions for quality:

```javascript
const allChats = ChatHistory.getAll();
allChats.forEach(chat => {
    if (chat.assistant.includes('error')) {
        console.warn('Error response detected:', chat);
    }
});
```

### 4. User Support

Export chat history for support tickets:

```javascript
// User reports an issue
const history = ChatHistory.exportAsJSON();
// Send to support team with issue report
```

## Storage Details

- **Storage Type**: `sessionStorage` (cleared when browser tab closes)
- **Storage Key**: `oic_complete_chat_history`
- **Max Entries**: 100 (oldest entries removed first)
- **Estimated Size**: ~50-100KB for typical session

## Browser Compatibility

Works in all modern browsers that support:
- `sessionStorage` API
- ES6 JavaScript features
- Blob API for file downloads

## Privacy & Security

✅ **Session-Only** - Data cleared when tab closes  
✅ **Client-Side** - No automatic server transmission  
✅ **User Control** - Export/clear functions available  
✅ **No PII** - Only chat content and context stored  

## Future Enhancements (Post-MVP)

- Server-side persistence option
- Database integration for long-term storage
- Multi-session history tracking
- Advanced analytics dashboard
- Chat history search functionality

## Troubleshooting

### History Not Persisting

Check browser console for errors:
```javascript
// Test storage availability
try {
    sessionStorage.setItem('test', 'test');
    sessionStorage.removeItem('test');
    console.log('sessionStorage available');
} catch (e) {
    console.error('sessionStorage not available:', e);
}
```

### Storage Quota Exceeded

Clear old history:
```javascript
ChatHistory.clear();
```

Or reduce max entries in `chat_sidebar.js`:
```javascript
maxEntries: 50  // Reduce from 100
```

## Support

For issues or questions about ChatHistory:
1. Check browser console for error messages
2. Verify `chat_sidebar.js` is loaded
3. Ensure `sessionStorage` is enabled in browser
4. Review this documentation

---

**Version**: v2-rag-enhanced  
**Last Updated**: November 2025  
**Module**: `chat_sidebar.js`
