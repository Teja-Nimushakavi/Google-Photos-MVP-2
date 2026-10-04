import chromadb
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
chroma = chromadb.PersistentClient(path="./chroma_db")
collection = chroma.get_collection(name="photos")

emb = client.models.embed_content(model='gemini-embedding-2', contents="whatsapp chats").embeddings[0].values
results = collection.query(query_embeddings=[emb], n_results=10)

print("Distances for 'whatsapp chats':")
for i in range(len(results['ids'][0])):
    meta = results['metadatas'][0][i]
    print(f"ID: {results['ids'][0][i]}, Distance: {results['distances'][0][i]:.3f}, URL: {meta.get('url', 'N/A')}")
