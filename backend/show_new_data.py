import chromadb
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection(name="photos")

results = collection.get()

new_photos = []
for i, pid in enumerate(results['ids']):
    if pid.startswith("photo_new_"):
        meta = results['metadatas'][i]
        doc = results['documents'][i]
        new_photos.append({"id": pid, "meta": meta, "doc": doc})

print(f"Found {len(new_photos)} newly processed images in the database.\n")
print("Here is a sample of the visual and metadata for 3 of the new images:\n")
print("="*60 + "\n")

for p in new_photos[:3]:
    meta = p['meta']
    print(f"Image URL: {meta.get('url', 'N/A')}")
    print(f"Caption: {meta.get('caption', 'N/A')}")
    
    print("\n--- Basic Metadata ---")
    print(f"- Location: {meta.get('location', 'N/A')}")
    print(f"- Environment: {meta.get('environment', 'N/A')}")
    print(f"- People: {meta.get('people', 'N/A')}")
    print(f"- Activity: {meta.get('activity', 'N/A')}")
    print(f"- Time: {meta.get('time', 'N/A')}")
    print(f"- Photo Type: {meta.get('photo_type', 'N/A')}")
    
    print("\n--- Visual Data (AI Extracted) ---")
    print(f"- Objects: {meta.get('objects', 'N/A')}")
    print(f"- Vibe: {meta.get('vibe', 'N/A')}")
    print(f"- Feeling: {meta.get('feeling', 'N/A')}")
    
    # Extract Detailed Description and Synonyms from the document text
    doc_parts = p['doc'].split(". ")
    print(f"- Document Text: {p['doc']}")
    
    print("\n" + "="*60 + "\n")
