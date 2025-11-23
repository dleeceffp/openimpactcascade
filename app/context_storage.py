"""
SQLite-based session storage for AssessmentContext.
Solves cookie size limit issue by storing context in database.

Design:
- Each session gets a unique session_id stored in a small cookie
- Full context data stored in SQLite database
- Automatic cleanup of old sessions
- Works with immutable containers (database in /tmp)
"""

import sqlite3
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict
import threading
import os

logger = logging.getLogger(__name__)


class ContextStorage:
    """
    SQLite-based storage for assessment contexts.
    Thread-safe and container-friendly.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize context storage.
        
        Args:
            db_path: Path to SQLite database. If None, uses /tmp for containers
        """
        if db_path is None:
            # Use /tmp for containers, or local temp for development
            db_dir = Path('/tmp' if os.path.exists('/tmp') else '.')
            db_path = db_dir / 'assessment_contexts.db'
        
        self.db_path = str(db_path)
        self.lock = threading.Lock()
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Context storage initialized at: {self.db_path}")
    
    def _init_database(self):
        """Create database schema if not exists."""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            try:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS assessment_contexts (
                        session_id TEXT PRIMARY KEY,
                        context_data TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        size_bytes INTEGER
                    )
                ''')
                
                # Index for cleanup queries
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_updated_at 
                    ON assessment_contexts(updated_at)
                ''')
                
                conn.commit()
                logger.info("Database schema initialized")
            finally:
                conn.close()
    
    def save(self, session_id: str, context_dict: Dict) -> bool:
        """
        Save assessment context to database.
        
        Args:
            session_id: Unique session identifier
            context_dict: Context data as dictionary
            
        Returns:
            True if saved successfully
        """
        try:
            context_json = json.dumps(context_dict)
            size_bytes = len(context_json.encode('utf-8'))
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    conn.execute('''
                        INSERT OR REPLACE INTO assessment_contexts 
                        (session_id, context_data, updated_at, size_bytes)
                        VALUES (?, ?, CURRENT_TIMESTAMP, ?)
                    ''', (session_id, context_json, size_bytes))
                    
                    conn.commit()
                    logger.debug(f"Saved context for session {session_id} ({size_bytes} bytes)")
                    return True
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"Error saving context for session {session_id}: {e}")
            return False
    
    def load(self, session_id: str) -> Optional[Dict]:
        """
        Load assessment context from database.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            Context dictionary or None if not found
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.execute(
                        'SELECT context_data FROM assessment_contexts WHERE session_id = ?',
                        (session_id,)
                    )
                    row = cursor.fetchone()
                    
                    if row:
                        context_dict = json.loads(row[0])
                        logger.debug(f"Loaded context for session {session_id}")
                        return context_dict
                    else:
                        logger.debug(f"No context found for session {session_id}")
                        return None
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"Error loading context for session {session_id}: {e}")
            return None
    
    def delete(self, session_id: str) -> bool:
        """
        Delete assessment context from database.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            True if deleted successfully
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    conn.execute(
                        'DELETE FROM assessment_contexts WHERE session_id = ?',
                        (session_id,)
                    )
                    conn.commit()
                    logger.info(f"Deleted context for session {session_id}")
                    return True
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"Error deleting context for session {session_id}: {e}")
            return False
    
    def cleanup_old_sessions(self, hours: int = 24) -> int:
        """
        Remove contexts older than specified hours.
        
        Args:
            hours: Age threshold in hours (default: 24)
            
        Returns:
            Number of sessions deleted
        """
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.execute(
                        'DELETE FROM assessment_contexts WHERE updated_at < ?',
                        (cutoff.isoformat(),)
                    )
                    deleted = cursor.rowcount
                    conn.commit()
                    
                    if deleted > 0:
                        logger.info(f"Cleaned up {deleted} old sessions (older than {hours}h)")
                    
                    return deleted
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"Error cleaning up old sessions: {e}")
            return 0
    
    def get_stats(self) -> Dict:
        """
        Get storage statistics.
        
        Returns:
            Dictionary with stats (total_sessions, total_size, oldest, newest)
        """
        try:
            with self.lock:
                conn = sqlite3.connect(self.db_path)
                try:
                    cursor = conn.execute('''
                        SELECT 
                            COUNT(*) as total_sessions,
                            SUM(size_bytes) as total_size,
                            MIN(updated_at) as oldest,
                            MAX(updated_at) as newest
                        FROM assessment_contexts
                    ''')
                    row = cursor.fetchone()
                    
                    return {
                        'total_sessions': row[0] or 0,
                        'total_size_bytes': row[1] or 0,
                        'oldest_session': row[2],
                        'newest_session': row[3]
                    }
                finally:
                    conn.close()
                    
        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            return {'error': str(e)}


# Global storage instance
_storage = None

def get_context_storage(db_path: str = None) -> ContextStorage:
    """
    Get or create global context storage instance.
    
    Args:
        db_path: Optional path to database file
        
    Returns:
        ContextStorage instance
    """
    global _storage
    if _storage is None:
        _storage = ContextStorage(db_path)
    return _storage
