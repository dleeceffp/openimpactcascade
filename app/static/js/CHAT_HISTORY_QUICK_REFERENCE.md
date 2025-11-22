# Chat History - Quick Reference Card

## 🎯 Quick Start

### View History in Console
```javascript
viewChatHistory();
```

### Get Statistics
```javascript
getChatStats();
// Returns: {totalExchanges: 15, pageBreakdown: {questionnaire: 10, results: 5}}
```

### Export History
```javascript
exportCompleteHistory();  // Text file
exportHistoryAsJSON();    // JSON file
```

### Clear History
```javascript
clearChatHistory();  // With confirmation
ChatHistory.clear(); // Direct
```

---

## 🔍 Debug Commands

### Check What's Stored
```javascript
// View in console
viewChatHistory();

// Get raw data
JSON.parse(sessionStorage.getItem('oic_complete_chat_history'));

// Check size
ChatHistory.getAll().length;
```

### Verify Persistence
```javascript
// On questionnaire page
console.log('Before:', ChatHistory.getAll().length);

// Navigate to results page
console.log('After:', ChatHistory.getAll().length);
// Should be same number
```

---

## 📊 Console Output Examples

### After Adding Message
```
[ChatHistory] Added entry. Total: 3 | Page: questionnaire
[ChatHistory] Current breakdown: {questionnaire: 3}
```

### On Page Load
```
[ChatHistory] Initialized with 3 entries
[ChatHistory] Loaded breakdown: {questionnaire: 3}
```

### On Results Page
```
[Results Page] ChatHistory on load: 3 entries
[Results Page] Breakdown: {questionnaire: 3}
```

---

## 🛠️ Common Tasks

### Test Storage Working
```javascript
try {
    sessionStorage.setItem('test', 'test');
    sessionStorage.removeItem('test');
    console.log('✅ sessionStorage working');
} catch (e) {
    console.error('❌ sessionStorage blocked:', e);
}
```

### Manual Add Entry
```javascript
ChatHistory.add(
    "Test question",
    "Test response",
    {page: "test", custom: "data"}
);
```

### Get Specific Page History
```javascript
const questionnaireChats = ChatHistory.getByPage('questionnaire');
console.log('Questionnaire messages:', questionnaireChats.length);
```

---

## 🚨 Troubleshooting

### History Shows 0 on Results Page
**Check:**
1. Console for errors
2. `sessionStorage.getItem('oic_complete_chat_history')`
3. Not in private/incognito mode
4. No ad blockers interfering

### Export Only Shows Current Page
**Fix:** Already fixed - `exportChat()` uses centralized history

### Duplicate Messages
**Fix:** Already implemented - duplicate detection active

---

## 📁 File Locations

- **Core Module:** `app/static/js/chat_sidebar.js`
- **Usage Guide:** `app/static/js/CHAT_HISTORY_USAGE.md`
- **Implementation:** `app/static/js/CHAT_HISTORY_IMPLEMENTATION.md`
- **This File:** `app/static/js/CHAT_HISTORY_QUICK_REFERENCE.md`

---

## 🔑 Key Points

✅ History persists across page navigation  
✅ Automatically cleared on home page  
✅ Real-time tracking (no delays)  
✅ Duplicate prevention built-in  
✅ Export includes all pages  
✅ Debug logging in console  

---

## 📞 Quick Help

**Not working?**
1. Check console logs
2. Run `viewChatHistory()`
3. Verify `sessionStorage` enabled
4. Review full documentation

**Working correctly?**
- Console shows page breakdown
- Export includes all pages
- History clears on home page
- Stats show correct counts

---

**Version:** v2-rag-enhanced  
**Last Updated:** November 2025
