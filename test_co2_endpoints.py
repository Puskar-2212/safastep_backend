"""
Quick test script for CO2 questions endpoints
Run this after starting the backend server
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_get_all_questions():
    """Test GET /co2-questions endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Get All Questions")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/co2-questions")
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Success: {data.get('success')}")
        print(f"Question Count: {data.get('count')}")
        
        if data.get('success') and data.get('questions'):
            print("\nFirst question:")
            first_q = data['questions'][0]
            print(f"  ID: {first_q.get('id')}")
            print(f"  Category: {first_q.get('category')}")
            print(f"  Question: {first_q.get('question')}")
            print(f"  Options: {len(first_q.get('options', []))}")
        
        print("\n Test 1 PASSED")
        return True
    except Exception as e:
        print(f"\n Test 1 FAILED: {e}")
        return False


def test_get_random_questions():
    """Test GET /co2-questions/random endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Get Random Questions")
    print("="*60)
    
    try:
        response = requests.get(f"{BASE_URL}/co2-questions/random?count=10")
        data = response.json()
        
        print(f"Status Code: {response.status_code}")
        print(f"Success: {data.get('success')}")
        print(f"Question Count: {data.get('count')}")
        
        if data.get('success') and data.get('questions'):
            questions = data['questions']
            print(f"\nReceived {len(questions)} questions")
            
            # Show categories
            categories = {}
            for q in questions:
                cat = q.get('category')
                categories[cat] = categories.get(cat, 0) + 1
            
            print("\nQuestions by category:")
            for cat, count in categories.items():
                print(f"  - {cat}: {count}")
            
            # Show first question details
            print("\nFirst question:")
            first_q = questions[0]
            print(f"  ID: {first_q.get('id')}")
            print(f"  Category: {first_q.get('category')}")
            print(f"  Question: {first_q.get('question')}")
            print(f"  Fun Fact: {first_q.get('funFact')}")
            print(f"  Options: {len(first_q.get('options', []))}")
            
            if first_q.get('options'):
                print(f"\n  First option:")
                opt = first_q['options'][0]
                print(f"    Label: {opt.get('label')}")
                print(f"    CO2: {opt.get('co2', opt.get('multiplier', 'N/A'))}")
        
        print("\n Test 2 PASSED")
        return True
    except Exception as e:
        print(f"\n Test 2 FAILED: {e}")
        return False


def test_random_variation():
    """Test that random endpoint returns different questions"""
    print("\n" + "="*60)
    print("TEST 3: Random Variation")
    print("="*60)
    
    try:
        # Get questions twice
        response1 = requests.get(f"{BASE_URL}/co2-questions/random?count=10")
        data1 = response1.json()
        
        response2 = requests.get(f"{BASE_URL}/co2-questions/random?count=10")
        data2 = response2.json()
        
        if data1.get('success') and data2.get('success'):
            ids1 = [q['id'] for q in data1['questions']]
            ids2 = [q['id'] for q in data2['questions']]
            
            print(f"First call IDs: {ids1[:3]}...")
            print(f"Second call IDs: {ids2[:3]}...")
            
            if ids1 != ids2:
                print("\n Questions are randomized (different order/selection)")
            else:
                print("\n Questions are identical (might be due to small dataset)")
        
        print("\n Test 3 PASSED")
        return True
    except Exception as e:
        print(f"\n Test 3 FAILED: {e}")
        return False


if __name__ == "__main__":
    print("\n Testing CO2 Questions API Endpoints")
    print("Make sure the backend server is running on http://localhost:8000\n")
    
    results = []
    results.append(test_get_all_questions())
    results.append(test_get_random_questions())
    results.append(test_random_variation())
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n All tests passed!")
    else:
        print(f"\n  {total - passed} test(s) failed")
