import main
import json

q = 'me on the beach with my family'
decomp = main.decompose_query(q)
search_text = main.build_search_text(decomp, [])

print(f'Search Text: {search_text}')

emb_response = main.client.models.embed_content(
    model='gemini-embedding-2',
    contents=search_text,
)
query_vector = emb_response.embeddings[0].values

chroma_results = main.collection.query(
    query_embeddings=[query_vector],
    n_results=10
)
distances = {}
for pid, dist in zip(chroma_results['ids'][0], chroma_results['distances'][0]):
    distances[pid] = dist

print('Top candidates:', distances)

photos_by_id = {p['id']: p for p in main.photos_db}
for pid in distances:
    photo = photos_by_id.get(pid)
    meta = photo.get('metadata', {})
    print(f'\nPID: {pid}')
    print(f'Meta location: {meta.get("location")}')
    
    if decomp.location and decomp.location_confidence == 'high':
        print(f'Location filter: query "{decomp.location.lower()}" in "{meta.get("location", "").lower()}"')
        if decomp.location.lower() not in meta.get("location", "").lower():
            print("FAILED LOCATION FILTER")
