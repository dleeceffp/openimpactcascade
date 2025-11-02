#!/usr/bin/env python3
"""
Abuse Investigation Utility

This script helps you respond to Anthropic abuse complaints by searching
your API call logs for specific users.

Usage Examples:
    # Search by hashed user ID (from Anthropic report)
    python investigate_abuse.py --hashed-id abc123def456...
    
    # Search by your internal user ID
    python investigate_abuse.py --user-id eval-user-abc123
    
    # Get user statistics
    python investigate_abuse.py --user-id eval-user-abc123 --stats
    
    # Search with custom date range
    python investigate_abuse.py --user-id eval-user-abc123 --days 60

Workflow for Responding to Anthropic Abuse Complaints:
1. Anthropic contacts you with a hashed user_id from their safeguards system
2. Run this script with --hashed-id to find all API calls from that user
3. Review the timestamps and metadata to identify the user in your system
4. Take appropriate action (warn, suspend, or ban the user)
5. Respond to Anthropic confirming action taken
"""

import argparse
import json
import sys
from datetime import datetime
from typing import List, Dict
from user_tracking import UserTracker


def format_timestamp(iso_timestamp: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return iso_timestamp


def display_api_call(call: Dict, index: int) -> None:
    """Display a single API call in a readable format."""
    print(f"\n{'='*70}")
    print(f"Call #{index + 1}")
    print(f"{'='*70}")
    print(f"Timestamp:       {format_timestamp(call['timestamp'])}")
    print(f"User ID:         {call['user_id']}")
    print(f"Hashed User ID:  {call['hashed_user_id'][:16]}...")
    print(f"API Type:        {call['api_type']}")
    print(f"Model:           {call['model']}")
    print(f"Request ID:      {call.get('request_id', 'N/A')}")
    
    if call.get('metadata'):
        print(f"\nMetadata:")
        for key, value in call['metadata'].items():
            print(f"  {key}: {value}")


def display_summary(calls: List[Dict]) -> None:
    """Display summary statistics for API calls."""
    if not calls:
        print("\nNo API calls found.")
        return
    
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"Total API Calls: {len(calls)}")
    
    # Count by API type
    api_types = {}
    for call in calls:
        api_type = call.get('api_type', 'unknown')
        api_types[api_type] = api_types.get(api_type, 0) + 1
    
    print(f"\nBreakdown by API Type:")
    for api_type, count in sorted(api_types.items()):
        print(f"  {api_type}: {count}")
    
    # Time range
    timestamps = [call['timestamp'] for call in calls]
    print(f"\nTime Range:")
    print(f"  First call: {format_timestamp(min(timestamps))}")
    print(f"  Last call:  {format_timestamp(max(timestamps))}")


def main():
    parser = argparse.ArgumentParser(
        description='Investigate API abuse complaints by searching user logs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Search parameters
    search_group = parser.add_mutually_exclusive_group(required=True)
    search_group.add_argument(
        '--user-id',
        help='Search by your internal user ID'
    )
    search_group.add_argument(
        '--hashed-id',
        help='Search by hashed user ID (from Anthropic report)'
    )
    
    # Options
    parser.add_argument(
        '--days',
        type=int,
        default=30,
        help='Number of days to search back (default: 30)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='Show statistics instead of detailed calls'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Maximum number of calls to display (default: 100)'
    )
    parser.add_argument(
        '--export',
        help='Export results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Initialize tracker
    tracker = UserTracker(session_based=False)
    
    # Determine search ID
    search_id = args.user_id or args.hashed_id
    
    # Search logs
    print(f"\n🔍 Searching logs for: {search_id}")
    print(f"   Date range: Last {args.days} days")
    print(f"   Please wait...\n")
    
    results = tracker.search_logs_by_user_id(search_id, days_back=args.days)
    
    if not results:
        print(f"\n❌ No API calls found for user: {search_id}")
        print(f"\nPossible reasons:")
        print(f"  - User ID is incorrect")
        print(f"  - Calls are older than {args.days} days")
        print(f"  - No logs exist for this user")
        sys.exit(1)
    
    # Limit results
    if len(results) > args.limit:
        print(f"⚠️  Found {len(results)} calls, showing first {args.limit}")
        print(f"   Use --limit to increase this number\n")
        results = results[:args.limit]
    
    # Display results
    if args.stats:
        # Show statistics only
        stats = tracker.get_user_stats(search_id, days_back=args.days)
        print(f"\n{'='*70}")
        print(f"USER STATISTICS")
        print(f"{'='*70}")
        print(json.dumps(stats, indent=2))
    else:
        # Show detailed calls
        for i, call in enumerate(results):
            display_api_call(call, i)
        
        display_summary(results)
    
    # Export if requested
    if args.export:
        try:
            with open(args.export, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n✅ Results exported to: {args.export}")
        except Exception as e:
            print(f"\n❌ Failed to export results: {e}")
    
    # Action recommendations
    print(f"\n{'='*70}")
    print(f"RECOMMENDED ACTIONS")
    print(f"{'='*70}")
    print(f"1. Review the API calls above to understand the violation")
    print(f"2. Identify the user in your system using the user_id")
    print(f"3. Take appropriate action:")
    print(f"   - First offense: Warn user about Anthropic's Usage Policy")
    print(f"   - Repeat offense: Suspend or ban user")
    print(f"4. Respond to Anthropic confirming action taken")
    print(f"5. Document the incident for your records")
    print(f"\nAnthropic Usage Policy: https://www.anthropic.com/legal/aup")
    print()


if __name__ == '__main__':
    main()
