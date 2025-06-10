# Travel Blog Mapper 🌍

This is a minimum viable data product created for the **Individual Assignment in the Minor: Data-Driven Decision Making**. It is a Flask-based web app that allows users to extract places from travel blogs, visualize them on a map, and automatically generate AI-powered travel itineraries.

---

## Features

- Extract place names from unstructured blog content
- Categorize places into Landmarks, Food & Drink, Transit, etc.
- Display markers on a map using Google Maps API
- Interactive marker removal and description addition
- AI-generated multi-day itinerary with walking routes
- Optional manual entry of places and dynamic anchor location

---

## Technologies Used

- **Python** & **Flask** (Backend)
- **spaCy** (NER for place detection)
- **Google Maps API** (Text Search + JS Maps)
- **Groq API** (for AI-based filtering and itinerary)
- **BeautifulSoup / regex** (HTML content parsing)
- **Bootstrap 5** (UI styling)

---

## 📁 Project Structure
  ├── app.py
  ├── templates/
  │ ├── index.html
  │ ├── map.html
  │ └── itinerary.html
  ├── static/
  ├── requirements.txt
  ├── worldcities.csv
  └── results.json

