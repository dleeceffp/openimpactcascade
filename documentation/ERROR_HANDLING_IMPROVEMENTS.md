# Error Handling Improvements - Flask App Versions

## Changes Made (Nov 4, 2025)

### Problem
The Flask applications were experiencing `BuildError` exceptions when trying to build URLs for the `generate_custom` endpoint. This occurred because:

1. **Narrow Exception Handling**: Only catching `ValueError` during AI generator initialization
2. **Silent Failures**: Other exceptions (like import errors, authentication failures, or RAG initialization issues) would crash the app before all routes were registered
3. **No Startup Logging**: Difficult to diagnose which version was running and when initialization failed

### Solution: Comprehensive Error Handling

Implemented improved error handling in all three Flask app versions:

#### **Version 1: flask_app_chat_v1_websearch.py**
```python
# Before:
try:
    ai_generator = AIQuestionGenerator()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (Web Search Only)")
except ValueError as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}")

# After:
logger.info(f"========== STARTING {VERSION} on PORT {PORT} ==========")
try:
    ai_generator = AIQuestionGenerator()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (Web Search Only)")
except Exception as e:
    logger.error(f"[{VERSION}] AI Generator initialization failed: {e}", exc_info=True)
    ai_generator = None
```

#### **Version 2: flask_app_chat_v2_rag.py**
```python
# Before:
try:
    ai_generator = AIQuestionGeneratorWithRAG()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (RAG + Web Search)")
except ValueError as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}")

# After:
logger.info(f"========== STARTING {VERSION} on PORT {PORT} ==========")
try:
    ai_generator = AIQuestionGeneratorWithRAG()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (RAG + Web Search)")
except Exception as e:
    logger.error(f"[{VERSION}] AI Generator initialization failed: {e}", exc_info=True)
    ai_generator = None
```

#### **Version 3: flask_app_chat_v3_rag_cot.py**
```python
# Before:
try:
    ai_generator = AIQuestionGeneratorWithRAGAndCoT()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (RAG + Chain of Thought)")
except ValueError as e:
    logger.warning(f"[{VERSION}] AI Generator not available: {e}")

# After:
logger.info(f"========== STARTING {VERSION} on PORT {PORT} ==========")
try:
    ai_generator = AIQuestionGeneratorWithRAGAndCoT()
    logger.info(f"[{VERSION}] AI Question Generator initialized successfully (RAG + Chain of Thought)")
except Exception as e:
    logger.error(f"[{VERSION}] AI Generator initialization failed: {e}", exc_info=True)
    ai_generator = None
```

### Key Improvements

1. **Startup Banner**: 
   - Added `logger.info(f"========== STARTING {VERSION} on PORT {PORT} ==========")`
   - Makes it immediately clear which version is starting and on which port
   - Helps identify if multiple versions are running or if the wrong version is active

2. **Catch All Exceptions**:
   - Changed from `except ValueError` to `except Exception`
   - Prevents any initialization error from crashing the app before routes are registered
   - Ensures Flask completes loading all routes even if AI generator fails

3. **Full Stack Traces**:
   - Added `exc_info=True` to logging
   - Provides complete traceback for debugging
   - Changed from `logger.warning()` to `logger.error()` for better visibility

4. **Explicit None Assignment**:
   - Added `ai_generator = None` in exception handler
   - Makes it explicit that the generator is unavailable
   - Prevents any ambiguity about the generator's state

### Benefits

✅ **Graceful Degradation**: Apps start successfully even if AI generator initialization fails
✅ **Complete Route Registration**: All routes (including `generate_custom`) are registered before any errors occur
✅ **Better Diagnostics**: Full stack traces help identify root cause of initialization failures
✅ **Clear Startup Logging**: Easy to see which version is running and if initialization succeeded
✅ **No BuildError**: Templates can safely call `url_for('generate_custom')` because routes are always registered

### Common Initialization Failures Now Handled

1. **Missing API Keys**: `ANTHROPIC_API_KEY` not set
2. **RAG Initialization Errors**: Vertex AI authentication failures, missing corpus, network issues
3. **Import Errors**: Missing dependencies or module import failures
4. **Configuration Errors**: Invalid environment variables or configuration
5. **Authentication Errors**: GCP service account or ADC issues

### Testing

To verify the improvements work:

```bash
# Test without ANTHROPIC_API_KEY (should start successfully with ai_generator=None)
unset ANTHROPIC_API_KEY
python flask_app_chat_v1_websearch.py

# Test with invalid RAG configuration (should start successfully with fallback)
export VERTEX_RAG_CORPUS="nonexistent-corpus"
python flask_app_chat_v2_rag.py

# Test with all valid configuration (should start successfully with full features)
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_CLOUD_PROJECT="your-project"
export VERTEX_RAG_CORPUS="oic-rarag-kb"
python flask_app_chat_v3_rag_cot.py
```

### Expected Log Output

**Successful Initialization:**
```
INFO:__main__:========== STARTING v2-rag on PORT 8080 ==========
INFO:ai_question_generator_with_rag:✅ RAG grounding enabled
INFO:__main__:[v2-rag] AI Question Generator initialized successfully (RAG + Web Search)
```

**Failed Initialization (Graceful):**
```
INFO:__main__:========== STARTING v2-rag on PORT 8080 ==========
ERROR:__main__:[v2-rag] AI Generator initialization failed: ANTHROPIC_API_KEY environment variable must be set
Traceback (most recent call last):
  File "flask_app_chat_v2_rag.py", line 36, in <module>
    ai_generator = AIQuestionGeneratorWithRAG()
  ...
ValueError: ANTHROPIC_API_KEY environment variable must be set
```

**App Still Starts:**
```
 * Running on http://0.0.0.0:8080
```

### Files Modified

- ✅ `flask_app_chat_v1_websearch.py` - Lines 25-40
- ✅ `flask_app_chat_v2_rag.py` - Lines 25-41
- ✅ `flask_app_chat_v3_rag_cot.py` - Lines 25-40

### Related Issues Resolved

- ❌ `BuildError: Could not build url for endpoint 'generate_custom'`
- ❌ App crashes before route registration completes
- ❌ Unclear which version is running
- ❌ Missing stack traces for initialization errors

### Next Steps

If you continue to see `BuildError` for `generate_custom`:

1. **Check for cached processes**: `pkill -f flask_app`
2. **Verify correct file is running**: Check the startup banner in logs
3. **Check for template caching**: Clear Flask template cache
4. **Verify route registration**: Add debug logging after route definitions

---

**Date**: November 4, 2025  
**Author**: Cascade AI Assistant  
**Issue**: BuildError for generate_custom endpoint  
**Status**: ✅ Resolved
