#!/usr/bin/env python3
"""
Verification script to confirm all AI generators have the required methods.
"""

import os
import sys

def check_file(filepath, filename):
    """Check if a file has the required methods."""
    print(f"\n{'='*70}")
    print(f"Checking: {filename}")
    print('='*70)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Check for required methods
    checks = {
        'generate_questionnaire': 'def generate_questionnaire(',
        'generate_custom_scenario_questionnaire': 'def generate_custom_scenario_questionnaire(',
        '_extract_json': 'def _extract_json(',
    }
    
    all_present = True
    for method_name, search_str in checks.items():
        if search_str in content:
            # Count occurrences
            count = content.count(search_str)
            # Find line number
            lines = content.split('\n')
            line_num = None
            for i, line in enumerate(lines, 1):
                if search_str in line:
                    line_num = i
                    break
            
            print(f"✅ {method_name:40s} Found at line {line_num}")
        else:
            print(f"❌ {method_name:40s} NOT FOUND")
            all_present = False
    
    return all_present

def main():
    print("\n" + "="*70)
    print("AI Question Generator Method Verification")
    print("="*70)
    
    files_to_check = [
        ('/mnt/user-data/uploads/ai_question_generator.py', 'v1 - ai_question_generator.py'),
        ('/mnt/user-data/outputs/ai_question_generator_with_rag.py', 'v2 - ai_question_generator_with_rag.py (FIXED)'),
        ('/mnt/user-data/outputs/ai_question_generator_with_rag_cot.py', 'v3 - ai_question_generator_with_rag_cot.py (FIXED)'),
    ]
    
    all_valid = True
    for filepath, name in files_to_check:
        if not check_file(filepath, name):
            all_valid = False
    
    print("\n" + "="*70)
    if all_valid:
        print("✅ SUCCESS: All generators have required methods")
        print("="*70)
        print("\nAll three versions now support:")
        print("  1. Standard generation (/generate)")
        print("  2. Custom scenario generation (/generate-custom)")
        print("\nYou can now test all three versions with both generation modes.")
    else:
        print("❌ FAILURE: Some generators are missing required methods")
        print("="*70)
    
    print()

if __name__ == "__main__":
    main()
