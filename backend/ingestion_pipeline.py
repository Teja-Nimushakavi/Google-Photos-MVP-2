import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
import chromadb
from chromadb.config import Settings
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "your_gemini_api_key_here":
    print("Error: GEMINI_API_KEY not set.")
    exit(1)
client = genai.Client(api_key=api_key)

# Initialize ChromaDB (Simulating Vector Database + Cloud Spanner metadata)
# We store both vectors and metadata in ChromaDB for simplicity of MVP.
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(
    name="photos",
    metadata={"hnsw:space": "cosine"} # using cosine similarity
)

# Schema for Vision Model extraction
class ExtractedFeatures(BaseModel):
    objects: List[str]
    vibe: str
    feeling: str
    detailed_description: str
    synonyms: List[str]

def ingest_dataset():
    dataset_path = "photos_dataset.json"
    with open(dataset_path, "r") as f:
        photos = json.load(f)

    print(f"Starting ingestion of {len(photos)} photos...")

    for i, photo in enumerate(photos):
        photo_id = photo["id"]
        # Skip if already in DB
        existing = collection.get(ids=[photo_id])
        if existing and existing["ids"]:
            print(f"Skipping {photo_id}, already in DB.")
            continue

        image_path = os.path.join(".", photo["url"].lstrip("/"))
        if not os.path.exists(image_path):
            print(f"Image not found: {image_path}")
            continue

        print(f"Processing {photo_id} ({i+1}/{len(photos)})...")
        
        try:
            # 1. Feature Extraction (Vision Model)
            is_video = image_path.lower().endswith((".mp4", ".mov", ".avi"))
            
            prompt = """
            Analyze this media and extract everyday, simple terminology that a normal person would use to search for this on their phone:
            1. objects: List of key objects visible (e.g., 'dog', 'coffee', 'car').
            2. vibe: The overall casual vibe (e.g., 'chill', 'fun party', 'lazy sunday', 'dark and gloomy'). Use very simple, conversational English.
            3. feeling: The basic emotion (e.g., 'happy', 'sad', 'lonely', 'excited', 'peaceful'). Use basic words only.
            4. detailed_description: A simple 2-3 sentence description of what is happening in plain, everyday English. Do not use professional, poetic, or complex language. Describe it exactly how a normal person would.
            5. synonyms: A list of 10-15 alternative keywords and synonyms that someone might type to find this (e.g., for a dog, include 'puppy', 'hound', 'pet', 'animal', 'canine').
            """
            
            if is_video:
                print(f"Uploading video {image_path} to Gemini for feature extraction...")
                media_content = client.files.upload(file=image_path)
                while media_content.state.name == "PROCESSING":
                    print(".", end="", flush=True)
                    time.sleep(2)
                    media_content = client.files.get(name=media_content.name)
                print(" Ready.")
                if media_content.state.name == "FAILED":
                    print(f"Failed to process video {image_path}")
                    continue
            else:
                from PIL import Image
                media_content = Image.open(image_path)
                
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=[media_content, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedFeatures,
                    temperature=0.2
                )
            )
            features = ExtractedFeatures.model_validate_json(response.text)
            
            # Combine extracted features with existing metadata
            meta = photo.get("metadata", {})
            meta["caption"] = photo.get("caption", "")
            meta["objects"] = ", ".join(features.objects)
            meta["vibe"] = features.vibe
            meta["feeling"] = features.feeling
            
            # 2. Multimodal Embedding Generation
            # We embed a rich text representation of the image combining description + vibes + metadata
            embedding_text = f"Description: {features.detailed_description}. Vibe: {features.vibe}. Feeling: {features.feeling}. Objects: {meta['objects']}. Synonyms: {', '.join(features.synonyms)}. Location: {meta.get('location', '')}. Time: {meta.get('time', '')}. Activity: {', '.join(meta.get('activity', []))}."
            
            emb_response = client.models.embed_content(
                model='gemini-embedding-2',
                contents=embedding_text,
            )
            vector = emb_response.embeddings[0].values
            
            # 3. Hybrid Storage Index
            # Store in ChromaDB
            # ChromaDB metadata values must be strings, ints, or floats
            flat_meta = {}
            for k, v in meta.items():
                if isinstance(v, list):
                    flat_meta[k] = ", ".join(v)
                else:
                    flat_meta[k] = str(v)
                    
            flat_meta["url"] = photo["url"]

            collection.add(
                ids=[photo_id],
                embeddings=[vector],
                metadatas=[flat_meta],
                documents=[embedding_text]
            )
            
            print(f"Successfully ingested {photo_id}")
            time.sleep(1) # Prevent rate limiting
            
        except Exception as e:
            print(f"Error processing {photo_id}: {e}")

    print("Ingestion complete!")

if __name__ == "__main__":
    ingest_dataset()
