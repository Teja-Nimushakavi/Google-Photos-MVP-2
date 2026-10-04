import os
import json
import time
from typing import List
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv
import chromadb
import uuid

load_dotenv()

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "your_gemini_api_key_here":
    print("Error: GEMINI_API_KEY not set in .env")
    exit(1)
client = genai.Client(api_key=api_key)

DATA_DIR = os.getenv("DATA_DIR", ".")
dataset_path = os.path.join(DATA_DIR, "photos_dataset.json")
images_dir = os.path.join(DATA_DIR, "static", "images")
os.makedirs(images_dir, exist_ok=True)

# Schema for new image basic metadata extraction
class ImageMetadata(BaseModel):
    caption: str
    location: str
    environment: List[str]
    people: List[str]
    activity: List[str]
    time: str
    photo_type: List[str]

def get_existing_urls():
    if not os.path.exists(dataset_path):
        return set()
    with open(dataset_path, "r") as f:
        photos = json.load(f)
    return {photo["url"].lstrip("/") for photo in photos}

def process_new_images():
    existing_urls = get_existing_urls()
    
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    new_images_found = False
    
    # 1. Generate basic metadata for new images/videos
    for filename in os.listdir(images_dir):
        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov", ".avi")):
            continue
            
        file_url = f"/static/images/{filename}"
        local_path = os.path.join(images_dir, filename)
        
        if local_path.replace("\\", "/") in existing_urls or local_path in existing_urls or file_url.lstrip("/") in existing_urls:
            continue
            
        safe_filename = filename.encode('ascii', 'ignore').decode('ascii')
        print(f"New media detected: {safe_filename}. Generating metadata...")
        new_images_found = True

        abs_path = os.path.abspath(local_path)
        if os.name == 'nt' and not abs_path.startswith('\\\\?\\'):
            abs_path = '\\\\?\\' + abs_path
        
        # We need a new ID
        photo_id = f"photo_new_{uuid.uuid4().hex[:8]}"
        
        # Determine if image or video
        is_video = filename.lower().endswith((".mp4", ".mov", ".avi"))
        
        prompt = """
        Analyze this media and provide basic metadata for a photo gallery app.
        1. caption: A short, descriptive caption of the media.
        2. location: A guess of the location (e.g., 'Home', 'Beach', 'Mountain', 'City', 'Cafe').
        3. environment: A list of tags like 'Indoor', 'Outdoor', 'Nature', 'Urban'.
        4. people: A list of tags like 'Alone', 'Friends', 'Family', 'Crowd', 'None'.
        5. activity: A list of tags describing what's happening (e.g., 'Walking', 'Eating', 'Working', 'Resting').
        6. time: A guess of the time of day (e.g., 'Morning', 'Day', 'Evening', 'Night').
        7. photo_type: A list of tags like 'Candid', 'Portrait', 'Landscape', 'Selfie', 'Macro', 'Video'.
        """
        
        try:
            if is_video:
                print(f"Uploading video {safe_filename} to Gemini...")
                media_content = client.files.upload(file=abs_path)
                # Wait for video processing
                while media_content.state.name == "PROCESSING":
                    print(".", end="", flush=True)
                    time.sleep(2)
                    media_content = client.files.get(name=media_content.name)
                print(" Ready.")
                if media_content.state.name == "FAILED":
                    print(f"Failed to process video {safe_filename}")
                    continue
            else:
                from PIL import Image
                media_content = Image.open(abs_path)
            
            response = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=[media_content, prompt],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ImageMetadata,
                    temperature=0.2
                )
            )
            
            meta_data = ImageMetadata.model_validate_json(response.text)
            
            new_entry = {
                "id": photo_id,
                "url": file_url,
                "caption": meta_data.caption,
                "metadata": {
                    "location": meta_data.location,
                    "environment": meta_data.environment,
                    "people": meta_data.people,
                    "activity": meta_data.activity,
                    "time": meta_data.time,
                    "photo_type": meta_data.photo_type
                }
            }
            dataset.append(new_entry)
            print(f"Added metadata for {safe_filename}")
            
            # Save incrementally
            with open(dataset_path, "w") as f:
                json.dump(dataset, f, indent=2)
                
            time.sleep(1) # rate limiting
            
        except Exception as e:
            print(f"Error generating metadata for {safe_filename}: {e}")

    if not new_images_found:
        print("No new images found to process. Please ensure new images are placed in 'backend/static/images/'")
        return
        
    print("Base metadata generation complete. Now running ingestion pipeline for vector embeddings...")
    
    # 2. Run ingestion pipeline for visual features and embeddings
    from ingestion_pipeline import ingest_dataset
    ingest_dataset()
    
    print("All new images have been fully processed and added to the database!")

if __name__ == "__main__":
    process_new_images()
