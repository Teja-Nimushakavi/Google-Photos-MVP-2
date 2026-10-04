import main

def test_query(q):
    print(f"\n--- Query: {q} ---")
    response = main.search_photos(q=q)
    results = response.results
    print(f"User Facing Query: {response.user_facing_query}")
    print(f"Results count: {len(results)}")
    if results:
        print(f"Top 3 results: {[r['id'] for r in results[:3]]}")
        for r in results[:2]:
            print(f"  {r['id']}: {r.get('caption')} (Score: {r.get('similarity_score')})")
    if response.needs_refinement:
        print(f"Needs Refinement: {response.refinement_question}")
        if response.smart_suggestion:
            print("  Suggestions:")
            for opt in response.smart_suggestion['options']:
                print(f"   - {opt['label']}")

if __name__ == "__main__":
    test_query("me on the beach with my family")
    test_query("driving at night")
    test_query("dog on couch")
    test_query("wedding")
    test_query("not with my friends")
