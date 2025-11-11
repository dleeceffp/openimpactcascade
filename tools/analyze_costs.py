#!/usr/bin/env python3
"""
Analyze API call logs by version for cost comparison.

Usage:
    python analyze_costs.py
    python analyze_costs.py --log-file ./logs/api_calls.jsonl
    python analyze_costs.py --version v2-rag
"""

import json
import argparse
from collections import defaultdict
from pathlib import Path
from datetime import datetime

# Claude Sonnet 4 pricing (per million tokens)
INPUT_COST_PER_M = 3.00
OUTPUT_COST_PER_M = 15.00

def analyze_logs(log_file='./logs/api_calls.jsonl', filter_version=None):
    """Analyze API calls by version."""
    
    stats = defaultdict(lambda: {
        'count': 0,
        'questionnaire_gen': 0,
        'chat_assist': 0,
        'users': set(),
        'request_ids': [],
        'timestamps': [],
        'rag_contexts': []
    })
    
    if not Path(log_file).exists():
        print(f"❌ Log file not found: {log_file}")
        print(f"   Make sure you've run the applications and generated some API calls.")
        return
    
    print(f"📊 Analyzing log file: {log_file}\n")
    
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entry = json.loads(line)
                version = entry.get('metadata', {}).get('version', 'unknown')
                
                # Filter by version if specified
                if filter_version and version != filter_version:
                    continue
                
                api_type = entry.get('api_type', 'unknown')
                user_id = entry.get('user_id', 'unknown')
                request_id = entry.get('request_id', 'unknown')
                timestamp = entry.get('timestamp', '')
                
                stats[version]['count'] += 1
                stats[version]['users'].add(user_id)
                stats[version]['request_ids'].append(request_id)
                stats[version]['timestamps'].append(timestamp)
                
                if api_type == 'questionnaire_generation':
                    stats[version]['questionnaire_gen'] += 1
                elif api_type == 'chat_assist':
                    stats[version]['chat_assist'] += 1
                
                # Track RAG usage
                metadata = entry.get('metadata', {})
                if 'rag_contexts_retrieved' in metadata:
                    stats[version]['rag_contexts'].append(metadata['rag_contexts_retrieved'])
                    
            except json.JSONDecodeError:
                continue
    
    if not stats:
        print("❌ No API calls found in log file.")
        if filter_version:
            print(f"   (filtered for version: {filter_version})")
        return
    
    # Print results
    print("="*70)
    print("API CALL ANALYSIS BY VERSION")
    print("="*70)
    
    total_calls = sum(s['count'] for s in stats.values())
    
    for version in sorted(stats.keys()):
        s = stats[version]
        
        print(f"\n{'='*70}")
        print(f"VERSION: {version}")
        print(f"{'='*70}")
        print(f"Total API Calls:           {s['count']:>6} ({s['count']/total_calls*100:>5.1f}%)")
        print(f"  Questionnaire Generation: {s['questionnaire_gen']:>6}")
        print(f"  Chat Assistance:          {s['chat_assist']:>6}")
        print(f"Unique Users:              {len(s['users']):>6}")
        
        # RAG statistics
        if s['rag_contexts']:
            avg_contexts = sum(s['rag_contexts']) / len(s['rag_contexts'])
            print(f"RAG Contexts Retrieved:    {len(s['rag_contexts']):>6} calls")
            print(f"  Average per call:        {avg_contexts:>6.1f}")
            print(f"  Total contexts:          {sum(s['rag_contexts']):>6}")
        
        # Time range
        if s['timestamps']:
            timestamps = [t for t in s['timestamps'] if t]
            if timestamps:
                first = min(timestamps)
                last = max(timestamps)
                print(f"Time Range:")
                print(f"  First call:  {first}")
                print(f"  Last call:   {last}")
        
        print(f"\nUser IDs:")
        for user_id in sorted(s['users']):
            user_calls = sum(1 for rid in s['request_ids'])
            print(f"  • {user_id}")
        
        print(f"\nRequest IDs (for Anthropic dashboard lookup):")
        for i, req_id in enumerate(s['request_ids'][:10], 1):
            print(f"  {i:>2}. {req_id}")
        if len(s['request_ids']) > 10:
            print(f"  ... and {len(s['request_ids']) - 10} more")
    
    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print(f"{'='*70}")
    
    print(f"\n{'Version':<15} {'Total Calls':<15} {'Quest. Gen':<15} {'Chat':<15}")
    print("-"*70)
    for version in sorted(stats.keys()):
        s = stats[version]
        print(f"{version:<15} {s['count']:<15} {s['questionnaire_gen']:<15} {s['chat_assist']:<15}")
    
    # Cost estimation note
    print(f"\n{'='*70}")
    print("COST ESTIMATION")
    print(f"{'='*70}")
    print(f"\n⚠️  Token usage data is not available in local logs.")
    print(f"    To get actual costs, check the Anthropic Console:")
    print(f"    https://console.anthropic.com/")
    print(f"\n    Filter by user ID prefix:")
    for version in sorted(stats.keys()):
        prefix = version
        print(f"      • {version}: eval-{prefix}-*")
    
    print(f"\n    Estimated cost per call (Claude Sonnet 4):")
    print(f"      • Questionnaire Generation: $0.04 - $0.08")
    print(f"      • Chat Assistance: $0.01 - $0.03")
    print(f"\n    Pricing:")
    print(f"      • Input:  ${INPUT_COST_PER_M:.2f} per million tokens")
    print(f"      • Output: ${OUTPUT_COST_PER_M:.2f} per million tokens")
    
    # Export request IDs for Anthropic lookup
    print(f"\n{'='*70}")
    print("EXPORT REQUEST IDs")
    print(f"{'='*70}")
    
    for version in sorted(stats.keys()):
        s = stats[version]
        output_file = f"request_ids_{version}.txt"
        with open(output_file, 'w') as f:
            for req_id in s['request_ids']:
                f.write(f"{req_id}\n")
        print(f"  ✓ {version}: {output_file} ({len(s['request_ids'])} request IDs)")
    
    print(f"\n{'='*70}")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze API call logs by version for cost comparison",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--log-file',
        default='./logs/api_calls.jsonl',
        help='Path to API call log file (default: ./logs/api_calls.jsonl)'
    )
    
    parser.add_argument(
        '--version',
        help='Filter by specific version (e.g., v1-web, v2-rag, v3-cot)'
    )
    
    args = parser.parse_args()
    
    analyze_logs(args.log_file, args.version)


if __name__ == '__main__':
    main()
