import json
import urllib.parse

# 50 Distinct Scenarios ensuring a diverse mix of people, places, times, and activities
scenarios = [
    # --- Friends & Outings ---
    ("Goa cafe with friends in the evening", "Goa", ["Indoor", "Cafe"], ["Friends"], ["Food"], "Evening", ["Group photo"]),
    ("Friends hiking up a lush green mountain", "Manali", ["Outdoor", "Nature", "Mountains"], ["Friends"], ["Trekking", "Travel"], "Morning", ["Group photo", "Landscape"]),
    ("Group of friends playing video games on a couch", "Home", ["Indoor", "Home"], ["Friends"], ["Gaming"], "Night", ["Candid"]),
    ("College farewell party with classmates dressed up", "Bangalore", ["Indoor", "College Campus", "Party"], ["Classmates"], ["Celebration", "College"], "Night", ["Group photo"]),
    ("Friends drinking beer at a rooftop bar", "Mumbai", ["Outdoor", "Bar"], ["Friends"], ["Drinking", "Party"], "Night", ["Candid"]),
    
    # --- Family ---
    ("Family having a picnic at the beach", "Kerala", ["Outdoor", "Beach"], ["Family"], ["Outing", "Food"], "Afternoon", ["Group photo"]),
    ("Parents and baby playing in the living room", "Home", ["Indoor", "Home"], ["Family", "Baby"], ["Playing"], "Morning", ["Candid"]),
    ("Big family dinner at a fancy restaurant", "Delhi", ["Indoor", "Restaurant"], ["Family"], ["Food", "Celebration"], "Evening", ["Group photo"]),
    ("Family walking through a colorful garden", "Ooty", ["Outdoor", "Garden", "Nature"], ["Family"], ["Outing"], "Afternoon", ["Candid", "Landscape"]),
    ("Kids building a snowman in the winter", "Shimla", ["Outdoor", "Snow"], ["Family"], ["Playing", "Travel"], "Morning", ["Group photo"]),
    
    # --- Couple / Romance ---
    ("Romantic dinner date with wine", "Paris", ["Indoor", "Restaurant"], ["Partner"], ["Date Night", "Food", "Drinking"], "Night", ["Portrait"]),
    ("Couple watching the sunset at the beach", "Goa", ["Outdoor", "Beach"], ["Partner"], ["Date Night", "Travel"], "Golden Hour", ["Landscape", "Silhouette"]),
    ("Selfie of a couple at a music concert", "Mumbai", ["Outdoor", "Concert", "Crowd"], ["Partner"], ["Music", "Concert"], "Night", ["Selfie"]),
    ("Couple cooking together in a modern kitchen", "Home", ["Indoor", "Kitchen"], ["Partner"], ["Cooking"], "Evening", ["Candid"]),
    ("Couple riding a bicycle in the park", "London", ["Outdoor", "Nature"], ["Partner"], ["Sports", "Outing"], "Morning", ["Candid"]),

    # --- Solo & Selfies ---
    ("Gym mirror selfie showing workout progress", "Gym", ["Indoor", "Gym"], ["Alone"], ["Workout"], "Morning", ["Mirror Selfie"]),
    ("Person reading a book by the window", "Home", ["Indoor", "Home"], ["Alone"], ["Reading"], "Raining", ["Candid"]),
    ("Solo traveler standing in front of a famous monument", "New York", ["Outdoor", "Urban"], ["Alone"], ["Travel", "Sightseeing"], "Day", ["Portrait"]),
    ("Person doing yoga on a mat in the living room", "Home", ["Indoor", "Home"], ["Alone"], ["Yoga", "Workout"], "Morning", ["Candid"]),
    ("Selfie at the airport terminal", "Airport", ["Indoor", "Airport"], ["Alone"], ["Travel"], "Morning", ["Selfie"]),

    # --- Work & Documents ---
    ("Electricity utility bill on a wooden table", "Home", ["Indoor", "Home"], ["None"], ["Work"], "Day", ["Bill", "Document"]),
    ("Close up of a restaurant dinner receipt", "Local City", ["Indoor", "Restaurant"], ["None"], ["Food"], "Night", ["Receipt", "Document"]),
    ("Flight boarding pass and a passport", "Airport", ["Indoor", "Airport"], ["None"], ["Travel"], "Day", ["Ticket", "Document"]),
    ("Meeting whiteboard notes in an office", "Office", ["Indoor", "Office"], ["None"], ["Work"], "Afternoon", ["Whiteboard", "Document"]),
    ("Screenshot of a funny WhatsApp chat", "Digital", ["Indoor"], ["None"], ["Gaming"], "Night", ["Screenshot"]),
    ("Close up of a driver's license ID card", "Home", ["Indoor", "Home"], ["None"], ["Work"], "Day", ["Document"]),

    # --- Pets ---
    ("Golden retriever dog sleeping on the couch", "Home", ["Indoor", "Home"], ["Pets"], ["Resting"], "Afternoon", ["Pet photo"]),
    ("Cat looking out the window at the rain", "Home", ["Indoor", "Home"], ["Pets"], ["Resting"], "Raining", ["Pet photo"]),
    ("Playing fetch with a dog in the park", "Local City", ["Outdoor", "Nature"], ["Pets"], ["Playing", "Outing"], "Morning", ["Pet photo"]),
    ("Selfie with a cute puppy", "Home", ["Indoor", "Home"], ["Pets", "Alone"], ["Playing"], "Day", ["Selfie", "Pet photo"]),

    # --- Objects & Specific Vibes ---
    ("A delicious slice of chocolate cake", "Cafe", ["Indoor", "Cafe"], ["None"], ["Food"], "Afternoon", ["Macro"]),
    ("Close up of a laptop on a desk with coffee", "Office", ["Indoor", "Office"], ["None"], ["Work"], "Morning", ["Macro"]),
    ("Keys to a new car on the dashboard", "Car", ["Indoor", "Car"], ["None"], ["Driving"], "Day", ["Macro"]),
    ("A red bicycle parked against a brick wall", "Street", ["Outdoor", "Urban"], ["None"], ["Travel"], "Day", ["Landscape"]),
    ("Acoustic guitar resting on an armchair", "Home", ["Indoor", "Home"], ["None"], ["Music"], "Evening", ["Candid"]),
    ("A neatly organized bookshelf", "Library", ["Indoor", "Library"], ["None"], ["Reading"], "Day", ["Landscape"]),
    
    # --- Sports & Hobbies ---
    ("Playing cricket in an empty ground", "Local City", ["Outdoor", "Stadium"], ["Friends"], ["Sports"], "Morning", ["Action"]),
    ("Swimming in a clear blue pool", "Hotel", ["Outdoor", "Pool"], ["Alone"], ["Sports", "Outing"], "Day", ["Action"]),
    ("Gardening and watering plants in the backyard", "Home", ["Outdoor", "Garden"], ["Alone"], ["Gardening"], "Evening", ["Candid"]),
    ("Painting on a canvas in a messy art studio", "Studio", ["Indoor", "Studio"], ["Alone"], ["Art", "Hobby"], "Day", ["Candid"]),

    # --- Urban & Nightlife ---
    ("Crowded nightclub with neon lights", "Club", ["Indoor", "Club"], ["Crowd"], ["Party", "Drinking"], "Night", ["Landscape"]),
    ("Traffic on a busy city street at night", "Mumbai", ["Outdoor", "Urban"], ["None"], ["Driving", "Travel"], "Night", ["Landscape"]),
    ("Shopping bags sitting on a bench in a mall", "Mall", ["Indoor", "Shopping Mall"], ["None"], ["Shopping"], "Afternoon", ["Candid"]),
    ("A cozy bookstore with warm lighting", "Local City", ["Indoor", "Shop"], ["None"], ["Reading", "Shopping"], "Evening", ["Landscape"]),

    # --- Events ---
    ("A beautiful Hindu wedding ceremony", "Temple", ["Indoor", "Temple"], ["Family", "Partner"], ["Wedding", "Celebration"], "Morning", ["Group photo", "Portrait"]),
    ("Birthday cake with lit candles", "Home", ["Indoor", "Home"], ["Friends"], ["Birthday", "Celebration"], "Night", ["Macro", "Candid"]),
    ("Graduation cap thrown in the air", "College", ["Outdoor", "College Campus"], ["Classmates"], ["Graduation"], "Day", ["Action"]),
    
    # --- Nature & Landscapes ---
    ("Beautiful sunset over the ocean", "Goa", ["Outdoor", "Beach", "Nature"], ["None"], ["Travel"], "Golden Hour", ["Landscape"]),
    ("Foggy morning in a dense pine forest", "Manali", ["Outdoor", "Nature", "Mountains"], ["None"], ["Trekking"], "Morning", ["Landscape"]),
    ("Close up of a vibrant red rose flower", "Garden", ["Outdoor", "Garden", "Nature"], ["None"], ["None"], "Day", ["Macro"])
]

dataset = []
for i, (caption, loc, env, ppl, act, time, ptype) in enumerate(scenarios):
    photo_id = f"photo_{i+1:03d}"
    
    # Use picsum.photos to get a random placeholder image
    url = f"https://picsum.photos/seed/photo_{i:03d}/1920/1440"
    
    dataset.append({
        "id": photo_id,
        "url": url,
        "caption": caption,
        "metadata": {
            "location": loc,
            "environment": env,
            "people": ppl,
            "activity": act,
            "time": time,
            "photo_type": ptype
        }
    })

with open('photos_dataset.json', 'w') as f:
    json.dump(dataset, f, indent=2)

print(f"Created photos_dataset.json with {len(dataset)} unique scenarios.")
