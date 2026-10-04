import os
import json
import time
from typing import List, Optional
from pydantic import BaseModel
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# Initialize Gemini Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key or api_key == "your_gemini_api_key_here":
    print("Error: GEMINI_API_KEY not set.")
    exit(1)
client = genai.Client(api_key=api_key)

class ImageMetadata(BaseModel):
    caption: str
    location: str
    environment: List[str]
    people: List[str]
    activity: List[str]
    time: str
    photo_type: List[str]

def process_image(photo):
    photo_id = photo["id"]
    image_path = os.path.join(".", photo["url"].lstrip("/"))
    
    if not os.path.exists(image_path):
        print(f"Skipping {photo_id}: Image not found at {image_path}")
        return photo
        
    try:
        img = Image.open(image_path)
        
        prompt = """
        Analyze this image and generate strictly accurate metadata categories that describe ONLY what is visible in the image.
        Categorize it using the following schema:
        - location: General location (e.g., Forest, City, Beach, Home, Office, Unknown)
        - environment: List of environments (e.g., Indoor, Outdoor, Nature, Cafe, Urban)
        - people: List of people types (e.g., Alone, Group, Crowd, None)
        - activity: List of activities happening (e.g., Walking, Eating, Resting, None)
        - time: Time of day (e.g., Day, Night, Evening, Morning, Unknown)
        - photo_type: Type of photo (e.g., Landscape, Portrait, Macro, Wildlife, Candid)
        - caption: A short, simple 1-sentence caption summarizing the image accurately.
        """
        
        response = client.models.generate_content(
            model='gemini-3.1-flash-lite',
            contents=[img, prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ImageMetadata,
                temperature=0.2
            )
        )
        
        extracted = ImageMetadata.model_validate_json(response.text)
        
        # Update the photo dictionary
        photo["caption"] = extracted.caption
        photo["metadata"] = {
            "location": extracted.location,
            "environment": extracted.environment,
            "people": extracted.people,
            "activity": extracted.activity,
            "time": extracted.time,
            "photo_type": extracted.photo_type
        }
        
        print(f"Successfully processed {photo_id}")
        return photo
        
    except Exception as e:
        print(f"Error processing {photo_id}: {e}")
        return photo

def main():
    dataset_path = "photos_dataset.json"
    with open(dataset_path, "r") as f:
        photos = json.load(f)
        
    print(f"Starting metadata correction for {len(photos)} photos...")
    
    updated_photos = []
    
    # Process serially to avoid rate limits
    for idx, photo in enumerate(photos):
        print(f"Processing {idx+1}/{len(photos)}...")
        updated = process_image(photo)
        updated_photos.append(updated)
        time.sleep(1) # Prevent rate limiting
        
        # Save incrementally every 10 images so we don't lose progress
        if (idx + 1) % 10 == 0:
            with open(dataset_path, "w") as f:
                json.dump(updated_photos + photos[idx+1:], f, indent=2)
                
    # Final save
    with open(dataset_path, "w") as f:
        json.dump(updated_photos, f, indent=2)
        
    print("Metadata correction complete!")

if __name__ == "__main__":
    main()
