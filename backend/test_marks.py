import main

queries = ["marks memo", "marks sheet", "marks"]

for q in queries:
    print(f"\n=== Query: {q} ===")
    decomp = main.decompose_query(q)
    print("Decomposition:")
    print(decomp.model_dump())
    
    response = main.search_photos(q=q)
    print(f"Results Count: {len(response.results)}")
    for r in response.results[:3]:
        print(f"  ID: {r['id']}, Score: {r.get('similarity_score')}, Caption: {r.get('caption')}")
        print(f"  Photo Type: {r.get('metadata', {}).get('photo_type')}")
