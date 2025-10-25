# API Safeguards Implementation

This document explains the Anthropic API safeguards implementation for OpenImpactCascade, following best practices from [Anthropic's API Safeguards documentation](https://support.claude.com/en/articles/9199617-api-safeguards-tools).

## Overview

We've implemented a comprehensive safeguards system that:
1. ✅ Assigns unique IDs to users
2. ✅ Passes cryptographically hashed IDs to Anthropic
3. ✅ Logs API calls with minimal data for abuse investigation
4. ✅ Enables free Anthropic safety filters (contact [email protected] to activate)
5. ✅ Provides tools for responding to abuse complaints

## Architecture

### Components

1. **`user_tracking.py`** - Core tracking module
   - Generates random user IDs (session-based for evaluation)
   - Hashes user IDs with SHA-256 (as recommended by Anthropic)
   - Logs API calls to daily JSONL files
   - Provides search utilities for abuse investigation

2. **`ai_question_generator.py`** - Updated to include user tracking
   - Accepts optional `user_id` parameter
   - Passes hashed `user_id` in API metadata
   - Logs all questionnaire generation calls

3. **`flask_app_chat.py`** - Updated to include user tracking
   - Generates session-based user IDs for evaluation
   - Passes hashed `user_id` in API metadata
   - Logs all chat assist calls

4. **`investigate_abuse.py`** - Abuse investigation utility
   - Searches logs by user ID or hashed ID
   - Displays API call history
   - Provides action recommendations

## How It Works

### User ID Flow

```
1. User makes request
   ↓
2. Generate/retrieve user_id (e.g., "eval-user-abc123")
   ↓
3. Hash user_id with SHA-256 (e.g., "a1b2c3d4...")
   ↓
4. Pass hashed ID to Anthropic in metadata
   ↓
5. Log: timestamp, user_id, hashed_id, api_type, request_id
   ↓
6. Store in daily log file (./logs/api_calls/YYYY-MM-DD_api_calls.jsonl)
```

### What Gets Logged

**Logged (minimal data for abuse investigation):**
- Timestamp
- Original user_id (for your internal use)
- Hashed user_id (what Anthropic sees)
- API type (questionnaire_generation, chat_assist)
- Model name
- Request ID (from Anthropic)
- Metadata (industry, region, etc.)

**NOT Logged (privacy-preserving):**
- User prompts
- API responses
- User account information
- Personal data

### Log File Format

Logs are stored as JSONL (JSON Lines) in `./logs/api_calls/`:

```json
{"timestamp": "2025-10-25T13:45:23Z", "user_id": "eval-user-abc123", "hashed_user_id": "a1b2c3d4...", "api_type": "questionnaire_generation", "model": "claude-sonnet-4-20250514", "request_id": "req_xyz789", "metadata": {"industry": "Healthcare", "region": "Canada"}}
```

## Current Mode: Evaluation

The system is currently in **evaluation mode** with session-based random user IDs:

- Each application start generates a new random user ID
- Format: `eval-user-{random-12-chars}`
- Allows you to test Anthropic's reporting without real user accounts

### Example Session

```python
# Application starts
Session User ID: eval-user-a1b2c3d4e5f6
Hashed User ID: 7f8e9d0c1b2a3f4e5d6c7b8a9f0e1d2c...

# User generates questionnaire
[2025-10-25 13:45:23] API call logged
  User: eval-user-a1b2c3d4e5f6
  Type: questionnaire_generation
  Request ID: req_xyz789
```

## Production Mode: Real Users

When you're ready to integrate with your registration system:

### 1. Update Flask App

```python
# In flask_app_chat.py, replace session-based tracking:

# OLD (evaluation mode):
tracker = get_tracker(session_based=True)
user_id = tracker.get_user_id()

# NEW (production mode):
from flask_login import current_user  # or your auth system
tracker = get_tracker(session_based=False)
user_id = tracker.get_user_id(provided_user_id=current_user.id)
```

### 2. User ID Format

Use stable, unique identifiers from your registration system:
- ✅ Good: `user-12345`, `uuid-abc-def-123`, `email-hash-xyz`
- ❌ Bad: Email addresses, names, or other PII

### 3. Free Tier Users

For one-time free users without accounts:
- Generate a unique ID on first use
- Store in session or cookie
- Still pass to Anthropic for tracking

## Responding to Abuse Complaints

When Anthropic contacts you about a violation:

### Step 1: Search Logs

Anthropic will provide the **hashed user_id** from their system:

```bash
python investigate_abuse.py --hashed-id a1b2c3d4e5f6...
```

This searches your logs and shows:
- All API calls from that hashed ID
- Your internal user_id
- Timestamps and metadata
- API types used

### Step 2: Identify User

Use the internal `user_id` to find the user in your system:
- Look up in your user database
- Check registration records
- Review account details

### Step 3: Take Action

Based on severity:
- **First offense**: Warn user about [Anthropic's Usage Policy](https://www.anthropic.com/legal/aup)
- **Repeat offense**: Suspend account temporarily
- **Severe violation**: Ban user permanently

### Step 4: Respond to Anthropic

Confirm action taken:
- User identified: Yes/No
- Action taken: Warning/Suspension/Ban
- Date of action
- Any additional context

### Example Investigation

```bash
$ python investigate_abuse.py --hashed-id a1b2c3d4e5f6...

🔍 Searching logs for: a1b2c3d4e5f6...
   Date range: Last 30 days
   Please wait...

======================================================================
Call #1
======================================================================
Timestamp:       2025-10-25 13:45:23 UTC
User ID:         eval-user-abc123
Hashed User ID:  a1b2c3d4e5f6...
API Type:        questionnaire_generation
Model:           claude-sonnet-4-20250514
Request ID:      req_xyz789

Metadata:
  industry: Healthcare
  region: Canada

======================================================================
SUMMARY
======================================================================
Total API Calls: 3

Breakdown by API Type:
  questionnaire_generation: 2
  chat_assist: 1

Time Range:
  First call: 2025-10-25 13:45:23 UTC
  Last call:  2025-10-25 14:30:15 UTC

======================================================================
RECOMMENDED ACTIONS
======================================================================
1. Review the API calls above to understand the violation
2. Identify the user in your system using the user_id
3. Take appropriate action:
   - First offense: Warn user about Anthropic's Usage Policy
   - Repeat offense: Suspend or ban user
4. Respond to Anthropic confirming action taken
5. Document the incident for your records
```

## Enabling Additional Safety Filters

Anthropic offers **free real-time moderation tooling** to detect harmful prompts:

### Contact Anthropic

Email: [email protected]

Request:
- Enable additional safety filters for your API key
- Specify your use case (risk assessment questionnaires)
- Mention you've implemented user tracking

### Benefits

- Real-time detection of harmful prompts
- Automatic blocking of policy violations
- Reduced abuse complaints
- Better user experience

## Testing the System

### 1. Test User Tracking

```bash
python user_tracking.py
```

This will:
- Generate a session user ID
- Simulate 3 API calls
- Search logs
- Display statistics

### 2. Test Investigation Tool

```bash
# Generate some test data first
python user_tracking.py

# Then investigate
python investigate_abuse.py --user-id eval-user-{your-id} --stats
```

### 3. Test in Flask App

```bash
# Start the app
python flask_app_chat.py

# Generate a questionnaire
# Check logs in ./logs/api_calls/
```

## Data Retention

- **Log files**: Stored indefinitely (you control retention)
- **Recommendation**: Keep logs for 90 days minimum
- **Compliance**: Ensure logs comply with your privacy policy
- **Cleanup**: Implement log rotation/archival as needed

## Privacy Considerations

### What Anthropic Receives

- Hashed user_id (SHA-256, irreversible)
- API requests and responses
- Safety classifier results

### What Anthropic Does NOT Receive

- Original user IDs
- User account information
- Email addresses or PII
- Your internal logs

### Your Logs

- Stored locally on your server
- Not shared with Anthropic
- Used only for abuse investigation
- Should comply with your privacy policy

## Security Best Practices

1. **Protect log files**: Restrict access to authorized personnel only
2. **Hash user IDs**: Always hash before sending to Anthropic
3. **Minimal logging**: Log only what's needed for abuse investigation
4. **Regular cleanup**: Archive or delete old logs per your policy
5. **Secure storage**: Encrypt logs at rest if storing sensitive metadata

## Compliance Checklist

- [x] User IDs assigned to API calls
- [x] User IDs cryptographically hashed before sending to Anthropic
- [x] API calls logged with minimal data
- [x] Investigation tools available for abuse complaints
- [ ] Additional safety filters enabled (contact Anthropic)
- [ ] User agreement includes Anthropic Usage Policy reference
- [ ] Privacy policy updated to reflect logging practices
- [ ] Log retention policy defined
- [ ] Abuse response procedures documented

## Support

### Anthropic Resources

- [API Safeguards Documentation](https://support.claude.com/en/articles/9199617-api-safeguards-tools)
- [Usage Policy](https://www.anthropic.com/legal/aup)
- [Commercial Terms](https://www.anthropic.com/legal/commercial-terms)
- Safety Filters: [email protected]

### Internal Resources

- `user_tracking.py` - Core tracking module
- `investigate_abuse.py` - Abuse investigation tool
- `./logs/api_calls/` - Log directory

## Future Enhancements

Potential improvements:
1. **Rate limiting**: Throttle users with high API usage
2. **Pre-moderation**: Check prompts before sending to Claude
3. **User warnings**: Automated warnings for policy violations
4. **Dashboard**: Web UI for viewing logs and statistics
5. **Alerts**: Notifications for suspicious activity
6. **Integration**: Connect with your user management system

## Questions?

For questions about this implementation:
1. Review Anthropic's safeguards documentation
2. Check the code comments in `user_tracking.py`
3. Test with `python user_tracking.py`
4. Contact Anthropic support for policy questions
