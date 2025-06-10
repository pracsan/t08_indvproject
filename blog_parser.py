import requests
from bs4 import BeautifulSoup

def get_blog_content(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    text = " ".join([para.get_text() for para in paragraphs])
    return text

url = "https://melangeoftales.com/bangalore-travel-blog/"

text = get_blog_content(url)
print(text)