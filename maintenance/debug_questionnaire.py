#!/usr/bin/env python3
"""
Debug script to check questionnaire file structure.
"""

import json
import sys
import os

def check_questionnaire(filepath):
    """Check questionnaire file structure."""
    print(f"\n{'='*60}")
    print(f"Checking: {filepath}")
    print(f"{'='*60}")
    
    # Check if file exists
    if not os.path.exists(filepath):
        print(f"❌ File does not exist: {filepath}")
        return
    
    # Get file size
    file_size = os.path.getsize(filepath)
    print(f"✅ File exists: {file_size} bytes")
    
    try:
        # Load JSON
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        print(f"✅ Valid JSON loaded")
        print(f"\nData type: {type(data)}")
        
        if isinstance(data, dict):
            print(f"\nTop-level keys: {list(data.keys())}")
            
            # Check for required fields
            required_fields = ['start_question_id', 'questions', 'metadata']
            for field in required_fields:
                if field in data:
                    print(f"  ✅ '{field}' present")
                    if field == 'start_question_id':
                        print(f"     Value: {data[field]}")
                    elif field == 'questions':
                        print(f"     Type: {type(data[field])}")
                        if isinstance(data[field], dict):
                            print(f"     Number of questions: {len(data[field])}")
                            print(f"     Question IDs: {list(data[field].keys())[:5]}...")
                        elif isinstance(data[field], list):
                            print(f"     ❌ ERROR: 'questions' is a list, should be dict!")
                            print(f"     Length: {len(data[field])}")
                    elif field == 'metadata':
                        print(f"     Keys: {list(data[field].keys())}")
                else:
                    print(f"  ❌ '{field}' MISSING")
            
            # Check if start_question_id exists in questions
            if 'start_question_id' in data and 'questions' in data:
                start_id = data['start_question_id']
                if isinstance(data['questions'], dict):
                    if start_id in data['questions']:
                        print(f"\n✅ Start question '{start_id}' exists in questions")
                    else:
                        print(f"\n❌ Start question '{start_id}' NOT FOUND in questions")
                        print(f"   Available question IDs: {list(data['questions'].keys())}")
            
            # Sample first question
            if 'questions' in data and isinstance(data['questions'], dict):
                first_key = list(data['questions'].keys())[0]
                first_q = data['questions'][first_key]
                print(f"\nFirst question sample:")
                print(f"  ID: {first_key}")
                print(f"  Keys: {list(first_q.keys())}")
                if 'text' in first_q:
                    print(f"  Text: {first_q['text'][:100]}...")
        
        elif isinstance(data, list):
            print(f"❌ ERROR: Root is a list (length: {len(data)}), should be dict!")
            if len(data) > 0:
                print(f"\nFirst item type: {type(data[0])}")
                if isinstance(data[0], dict):
                    print(f"First item keys: {list(data[0].keys())}")
        
        print(f"\n{'='*60}")
        print("✅ File structure check complete")
        print(f"{'='*60}\n")
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON decode error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        filepath = sys.argv[1]
    else:
        # Default to most recent v2-rag file
        import glob
        files = glob.glob('./generated/v2-rag*.json')
        if files:
            filepath = max(files, key=os.path.getctime)
            print(f"Using most recent file: {filepath}")
        else:
            print("No v2-rag files found. Usage: python debug_questionnaire.py <filepath>")
            sys.exit(1)
    
    check_questionnaire(filepath)
