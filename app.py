from flask import Flask, render_template, request, session, redirect, url_for
import requests
import re
import spacy
import json
# from blog_parser import get_blog_content


from math import radians, cos, sin, asin, sqrt

app = Flask(__name__)
GOOGLE_API_KEY = "key"  # Replace with your actual key
app.secret_key = "key"



nlp = spacy.load("en_core_web_sm")


ANCHOR_LOCATIONS = {
    "Bangalore": (12.9716, 77.5946),
    "Mumbai": (19.0760, 72.8777),
    "Lisbon": (38.7223, -9.1393),
    "Paris": (48.8566, 2.3522),
    "Amsterdam": (52.3676, 4.9041),
    "Rome": (41.9028, 12.4964)
}


def get_blog_content(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', '', response.text))
    except Exception as e:
        print("Error fetching blog:", e)
    return ""


def haversine_distance(lat1, lng1, lat2, lng2):
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2)**2
    return 6371 * 2 * asin(sqrt(a))


def find_place_on_google(query, api_key):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = { "query": query, "key": api_key }
    response = requests.get(url, params=params)
    data = response.json()
    if data.get("results"):
        result = data["results"][0]
        location = result["geometry"]["location"]
        return {
            "name": result["name"],
            "lat": location["lat"],
            "lng": location["lng"]
        }
    return None


def extract_anchor(text):
    doc = nlp(text)
    cities = [ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC")]
    if not cities:
        return None
    return max(set(cities), key=cities.count)


def classify(name):
    name = name.lower()
    if any(x in name for x in ["museum", "monument", "palace", "park", "house", "square", "synagogue"]):
        return "Landmark"
    elif any(x in name for x in ["restaurant", "cafe", "bar", "brewpub", "eat", "pancake", "food"]):
        return "Food & Drink"
    elif any(x in name for x in ["station", "residency", "airport", "terminal", "centraal"]):
        return "Transit / Misc"
    return "General"

GROQ_API_KEY = "key"
def filter_valid_places(results, api_key):
    place_names = [place["name"] for place in results]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": """You are a geolocation assistant. 
You will be given a list of places. 
Return only the ones that are a tourist would like to go to including cafes, restaurants, parks, museums, etc. Return atleast 15 places.
Respond only in this JSON format:

{
  "valid_places": ["Place A", "Place B"]
}"""
            },
            {
                "role": "user",
                "content": f"Here is the list: {place_names}"
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    data = response.json()

    # Parse JSON content string safely
    content_str = data["choices"][0]["message"]["content"]
    content_data = json.loads(content_str)
    valid_place_names = content_data.get("valid_places", [])

    return [place for place in results if place["name"] in valid_place_names]


@app.route('/', methods=['GET', 'POST'], endpoint='map_page')
def home():
    if request.method == 'POST':
        blog_url = request.form['blog_url']
        selected_location = request.form['location']
        manual_place = request.form.get('manual_place', '').strip()

        blog_text = get_blog_content(blog_url)

        anchor = ANCHOR_LOCATIONS.get(selected_location)
        if not anchor:
            inferred = extract_anchor(blog_text)
            anchor = ANCHOR_LOCATIONS.get(inferred, ANCHOR_LOCATIONS["Bangalore"])

        raw_candidates = re.findall(r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+){0,3})\b', blog_text)

        junk_words = {
            "thanks", "subscribe", "support", "foundation", "academy", "media", "marketing",
            "insurance", "solutions", "privacy", "terms", "cookies", "october", "soon",
            "when", "back", "newsletter", "development", "policy", "disclosure", "contact",
            "symbol", "b.v.", "bv", "group", "systems", "solution", "extension"
        }

        filtered = set([
            phrase for phrase in raw_candidates
            if (
                len(phrase) >= 3 and
                len(phrase.split()) <= 4 and
                not any(j in phrase.lower() for j in junk_words) and
                not re.search(r'\b(bv|b\.v\.|vereniging)\b', phrase.lower()) and
                not phrase.lower().startswith(("thanks", "contact", "terms")) and
                not phrase.lower() in ["one", "two", "some", "any", "how", "what", "where", "when", "why"]
            )
        ])

        if manual_place:
            filtered.add(manual_place.strip())

        print(f"\n🧐 Candidate pool ({len(filtered)}):")
        for phrase in sorted(filtered):
            print("-", phrase)

        print(f"\n🔍 Querying {len(filtered)} place candidates...\n")
        results = []
        seen_coords = set()

        for name in sorted(filtered):
            print(f"➡ Trying: {name}")
            result = find_place_on_google(name, GOOGLE_API_KEY)
            if result:
                dist = haversine_distance(result["lat"], result["lng"], anchor[0], anchor[1])
                coords = (round(result["lat"], 6), round(result["lng"], 6))
                if dist <= 50 and coords not in seen_coords:
                    result["type"] = classify(result["name"])
                    print(f"✅ Found: {result['name']} ({result['lat']}, {result['lng']}) [Type: {result['type']}]")
                    results.append(result)
                    seen_coords.add(coords)
                else:
                    print(f"❌ Too far or duplicate: {name} ({dist:.1f} km)")
            else:
                print(f"❌ No match on Google: {name}")

        print(f"\n✅ Total accepted: {len(results)}\n")
        
        import json
        with open('results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print("Results saved to results.json")

        try:
            results = filter_valid_places(results, GROQ_API_KEY)
            for i in results:
                print(i["name"])
            print(f"✅ Total accepted after local filtering: {len(results)}\n")
        except Exception as e:
            print(f"❌ Groq filtering failed: {e}")

        session["places"] = results
        session["selected_location"] = selected_location

        return render_template('map.html', places=results, api_key=GOOGLE_API_KEY, selected_location=selected_location)

    elif request.method == 'GET':
        if request.args.get("from") == "itinerary":
            existing_places = session.get("places", [])
            selected_location = session.get("selected_location", "")
            if existing_places:
                return render_template('map.html', places=existing_places, api_key=GOOGLE_API_KEY, selected_location=selected_location)

    # No session or itinerary redirect → clear and go to home
    session.pop("places", None)
    session.pop("selected_location", None)
    return render_template('index.html', places=[], api_key=GOOGLE_API_KEY, selected_location="")




@app.route('/itinerary', methods=['GET', 'POST'])
def itinerary():
    print("Itinerary route triggered")

    if request.method == 'POST':
        try:
            filtered = request.form.get("filtered_places")
            if not filtered:
                return redirect("/")
            results = json.loads(filtered)
            session["places"] = results  # ✅ Save filtered list to session
        except Exception as e:
            print("❌ Failed to load filtered places:", e)
            return redirect("/")
    else:
        results = session.get("places", [])
        if not results:
            return redirect("/")

    place_names = [place["name"] for place in results]

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "llama3-70b-8192",
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {
                "role": "system",
                "content": """You are a helpful travel assistant. Group a list of tourist places into daily itineraries.
Return JSON like this:
{
  "Day 1": ["Place A", "Place B", ...],
  "Day 2": ["Place C", "Place D", ...]
}"""
            },
            {
                "role": "user",
                "content": f"Group these places for a tourist trip: {place_names}"
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        raw_response = response.json()
        content_str = raw_response["choices"][0]["message"]["content"]
        print("🧠 Raw AI content:", content_str)
        itinerary_data = json.loads(content_str)
    except Exception as e:
        print("🛑 Groq raw response text:", response.text)
        print("🛑 Error when parsing:", e)
        return render_template("itinerary.html", days={}, api_key=GOOGLE_API_KEY, error=str(e))

    # Map full place objects to each day
    name_to_place = {p["name"]: p for p in results}
    days = {
        day: [name_to_place[name] for name in names if name in name_to_place]
        for day, names in itinerary_data.items()
    }

    return render_template("itinerary.html", days=days, api_key=GOOGLE_API_KEY)

if __name__ == '__main__':
    app.run(debug=True)
    