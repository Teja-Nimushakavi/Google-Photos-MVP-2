import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

def download_image(photo):
    url = photo["url"]
    photo_id = photo["id"]
    filepath = os.path.join(IMAGE_DIR, f"{photo_id}.jpg")
    
    # Check if we already have it so we don't re-download unnecessarily
    if not os.path.exists(filepath):
        try:
            print(f"Downloading {photo_id}...")
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response, open(filepath, 'wb') as out_file:
                data = response.read()
                out_file.write(data)
        except Exception as e:
            print(f"Failed to download {photo_id}: {e}")
            return photo
    
    # Update url to local path
    photo["url"] = f"/static/images/{photo_id}.jpg"
    return photo

def main():
    global IMAGE_DIR
    IMAGE_DIR = os.path.join(os.path.dirname(__file__), "static", "images")
    os.makedirs(IMAGE_DIR, exist_ok=True)
    
    json_path = os.path.join(os.path.dirname(__file__), "photos_dataset.json")
    with open(json_path, "r") as f:
        dataset = json.load(f)
        
    print(f"Starting download of {len(dataset)} images to {IMAGE_DIR}...")
    
    updated_dataset = []
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(download_image, photo): photo for photo in dataset}
        for future in as_completed(futures):
            updated_photo = future.result()
            updated_dataset.append(updated_photo)
            
    # Sort dataset by id to maintain order
    updated_dataset.sort(key=lambda x: x["id"])
    
    with open(json_path, "w") as f:
        json.dump(updated_dataset, f, indent=2)
        
    print(f"Successfully downloaded images and updated {json_path}")

if __name__ == "__main__":
    main()
