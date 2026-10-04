import main

def debug_search(q):
    print(f"\n=== Debug Query: {q} ===")
    parsed = main.parse_query_with_gemini(q)
    print(f"Parsed Tags: {parsed}")
    
    search_text = parsed.search_terms if parsed.search_terms else q
    print(f"Search Text: {search_text}")
    
    emb_response = main.client.models.embed_content(
        model='gemini-embedding-2',
        contents=search_text,
    )
    query_vector = emb_response.embeddings[0].values
    
    chroma_results = main.collection.query(
        query_embeddings=[query_vector],
        n_results=5
    )
    print("Top 5 distances:")
    for pid, dist in zip(chroma_results["ids"][0], chroma_results["distances"][0]):
        print(f"  {pid}: {dist}")

if __name__ == "__main__":
    debug_search("flag")
    debug_search("American")
    debug_search("flg")
