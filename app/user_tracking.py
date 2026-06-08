"""
User tracking and logging for Anthropic API safeguards compliance.

This module provides:
1. Random user ID generation for evaluation/testing
2. Cryptographic hashing of user IDs (as recommended by Anthropic)
3. Minimal logging of API calls with end-user-id for abuse investigation
4. Log search utilities for responding to Anthropic abuse complaints

Per Anthropic's API Safeguards documentation:
- Store IDs linked with each API call for violation tracking
- Pass hashed IDs to Anthropic for precise violation pinpointing
- Enable response to abuse complaints without storing long-term account data
"""

import os
import json
import hashlib
import uuid
from datetime import datetime
from typing import Optional, Dict, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log directory
LOG_DIR = './logs/api_calls'
os.makedirs(LOG_DIR, exist_ok=True)


from config import OIC_MODEL

class UserTracker:
    """Manages user ID generation, hashing, and API call logging."""
    
    def __init__(self, session_based: bool = True, code_generator: str = "wsa"):
        """
        Initialize user tracker.
        
        Args:
            session_based: If True, generates a random user ID per session (for evaluation).
                          If False, expects user IDs to be provided from registration system.
            code_generator: Identifier for the code generator/tree (e.g., 'wsa' for Windsurf Anthropic).
                          Used to distinguish between competing implementations during testing.
        """
        self.session_based = session_based
        self.code_generator = code_generator
        self.session_user_id = None
        
        if session_based:
            self.session_user_id = self._generate_session_user_id()
            logger.info(f"Generated session user ID: {self.session_user_id} (code_generator: {self.code_generator})")
    
    def _generate_session_user_id(self) -> str:
        """Generate a random user ID for this session (evaluation mode)."""
        return f"eval-{self.code_generator}-{uuid.uuid4().hex[:12]}"
    
    def hash_user_id(self, user_id: str) -> str:
        """
        Create a cryptographic hash of the user ID.
        
        Per Anthropic's recommendation: "To help protect end-users' privacy, 
        any IDs passed should be cryptographically hashed."
        
        Args:
            user_id: The original user identifier
            
        Returns:
            SHA-256 hash of the user ID (hex string)
        """
        return hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    
    def get_user_id(self, provided_user_id: Optional[str] = None) -> str:
        """
        Get the user ID to use for this request.
        
        Args:
            provided_user_id: User ID from registration system (if available)
            
        Returns:
            User ID (session-based or provided)
        """
        if provided_user_id:
            return provided_user_id
        elif self.session_based and self.session_user_id:
            return self.session_user_id
        else:
            # Fallback: generate a one-time ID
            return f"anonymous-{uuid.uuid4().hex[:8]}"
    
    def log_api_call(
        self,
        user_id: str,
        hashed_user_id: str,
        api_type: str,
        model: str,
        request_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Log an API call with minimal information for abuse investigation.
        
        Stores only:
        - Timestamp
        - User ID (original, for your internal use)
        - Hashed user ID (what was sent to Anthropic)
        - API type (questionnaire generation, chat assist, etc.)
        - Model used
        - Request ID (from Anthropic response headers)
        
        Does NOT store:
        - Prompts
        - Responses
        - Any user account information
        
        Args:
            user_id: Original user identifier
            hashed_user_id: Hashed version sent to Anthropic
            api_type: Type of API call (e.g., 'questionnaire_generation', 'chat_assist')
            model: Model name used
            request_id: Request ID from Anthropic response (if available)
            metadata: Optional additional metadata (industry, region, etc.)
        """
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'user_id': user_id,
            'hashed_user_id': hashed_user_id,
            'api_type': api_type,
            'model': model,
            'request_id': request_id,
            'metadata': metadata or {}
        }
        
        # Log to daily file
        log_filename = f"{datetime.utcnow().strftime('%Y-%m-%d')}_api_calls.jsonl"
        log_path = os.path.join(LOG_DIR, log_filename)
        
        try:
            with open(log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            logger.info(f"Logged API call: user={user_id}, type={api_type}, request_id={request_id}")
        except Exception as e:
            logger.error(f"Failed to log API call: {e}")
    
    def search_logs_by_user_id(
        self,
        user_id: str,
        days_back: int = 30
    ) -> List[Dict]:
        """
        Search logs for all API calls by a specific user ID.
        
        Use this when responding to an Anthropic abuse complaint:
        1. Anthropic provides you with the hashed user ID from their report
        2. You search your logs to find the original user ID
        3. You can then warn/suspend the user
        
        Args:
            user_id: User ID to search for (original or hashed)
            days_back: Number of days to search back
            
        Returns:
            List of matching log entries
        """
        matches = []
        
        # Determine if we're searching by original or hashed ID
        is_hash = len(user_id) == 64 and all(c in '0123456789abcdef' for c in user_id.lower())
        search_field = 'hashed_user_id' if is_hash else 'user_id'
        
        logger.info(f"Searching logs for {search_field}={user_id} (last {days_back} days)")
        
        # Search through log files
        from datetime import timedelta
        current_date = datetime.utcnow()
        
        for day_offset in range(days_back):
            search_date = current_date - timedelta(days=day_offset)
            log_filename = f"{search_date.strftime('%Y-%m-%d')}_api_calls.jsonl"
            log_path = os.path.join(LOG_DIR, log_filename)
            
            if not os.path.exists(log_path):
                continue
            
            try:
                with open(log_path, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        
                        entry = json.loads(line)
                        if entry.get(search_field) == user_id:
                            matches.append(entry)
            except Exception as e:
                logger.error(f"Error reading log file {log_filename}: {e}")
        
        logger.info(f"Found {len(matches)} matching API calls")
        return matches
    
    def get_user_stats(self, user_id: str, days_back: int = 7) -> Dict:
        """
        Get usage statistics for a user (for rate limiting, abuse detection).
        
        Args:
            user_id: User ID to analyze
            days_back: Number of days to analyze
            
        Returns:
            Dictionary with usage statistics
        """
        logs = self.search_logs_by_user_id(user_id, days_back)
        
        if not logs:
            return {
                'user_id': user_id,
                'total_calls': 0,
                'days_analyzed': days_back
            }
        
        api_types = {}
        for log in logs:
            api_type = log.get('api_type', 'unknown')
            api_types[api_type] = api_types.get(api_type, 0) + 1
        
        return {
            'user_id': user_id,
            'total_calls': len(logs),
            'days_analyzed': days_back,
            'api_types': api_types,
            'first_call': logs[-1]['timestamp'] if logs else None,
            'last_call': logs[0]['timestamp'] if logs else None
        }


# Global tracker instance
_tracker = None

def get_tracker(session_based: bool = True, code_generator: str = "wsa") -> UserTracker:
    """
    Get or create the global user tracker instance.
    
    Args:
        session_based: If True, generates random user IDs per session
        code_generator: Identifier for code generator/tree (e.g., 'wsa' for Windsurf Anthropic)
    
    Returns:
        UserTracker instance
    """
    global _tracker
    if _tracker is None:
        _tracker = UserTracker(session_based=session_based, code_generator=code_generator)
    return _tracker


def create_api_metadata(user_id: Optional[str] = None) -> Dict:
    """
    Create metadata dictionary for Anthropic API calls.
    
    This includes the hashed user_id that Anthropic recommends for
    precise violation tracking.
    
    Args:
        user_id: User ID (if None, uses session-based ID)
        
    Returns:
        Dictionary with 'user_id' field containing hashed ID
    """
    tracker = get_tracker()
    original_user_id = tracker.get_user_id(user_id)
    hashed_user_id = tracker.hash_user_id(original_user_id)
    
    return {
        'user_id': hashed_user_id,
        '_original_user_id': original_user_id  # Store for logging, not sent to API
    }


if __name__ == '__main__':
    # Example usage and testing
    print("=== User Tracking System Test ===\n")
    
    # Initialize tracker in session-based mode (for evaluation)
    tracker = UserTracker(session_based=True)
    print(f"Session User ID: {tracker.session_user_id}")
    print(f"Hashed User ID: {tracker.hash_user_id(tracker.session_user_id)}\n")
    
    # Simulate some API calls
    print("Simulating API calls...")
    for i in range(3):
        user_id = tracker.get_user_id()
        hashed_id = tracker.hash_user_id(user_id)
        
        tracker.log_api_call(
            user_id=user_id,
            hashed_user_id=hashed_id,
            api_type='questionnaire_generation' if i % 2 == 0 else 'chat_assist',
            model=OIC_MODEL,
            request_id=f'req_{uuid.uuid4().hex[:16]}',
            metadata={'industry': 'Healthcare', 'region': 'Canada'}
        )
    
    print(f"\nLogged {3} API calls\n")
    
    # Search logs
    print("Searching logs by user ID...")
    results = tracker.search_logs_by_user_id(tracker.session_user_id)
    print(f"Found {len(results)} calls for user {tracker.session_user_id}\n")
    
    # Get stats
    print("User statistics:")
    stats = tracker.get_user_stats(tracker.session_user_id)
    print(json.dumps(stats, indent=2))
    
    print("\n=== Test Complete ===")
    print(f"Log files created in: {LOG_DIR}")
