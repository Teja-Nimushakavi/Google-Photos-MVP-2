import main

response = main.search_photos(q="whatsapp chats")
for r in response.results:
    print(f"ID: {r['id']}")
    print(f"  Caption: {r.get('caption')}")
    print(f"  Photo Type: {r.get('metadata', {}).get('photo_type')}")
    print(f"  Similarity Score: {r.get('similarity_score')}")
