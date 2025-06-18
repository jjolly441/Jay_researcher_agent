from openai import OpenAI

client = OpenAI()
import os
import openai
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# Load your OpenAI API key securely
openai.api_key = os.getenv("OPENAI_API_KEY")

# Step 1: Get user query
query = input("🔍 What would you like me to research?\n> ")

# Step 2: Search the web using DuckDuckGo
print("\n🔎 Searching the web...")
urls = []

with DDGS() as ddgs:
  results = ddgs.text(query, max_results=3)
  for result in results:
    urls.append(result["href"])


# Step 3: Scrape article content
def get_text_from_url(url):
  try:
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    paragraphs = soup.find_all('p')
    return ' '.join([p.get_text() for p in paragraphs])
  except Exception as e:
    print(f"Error scraping {url}: {e}")
    return ""


all_text = ""
for url in urls:
  print(f"📄 Scraping: {url}")
  page_text = get_text_from_url(url)
  all_text += page_text + "\n\n"

# Limit text to first ~4,000 tokens (OpenAI input limit)
all_text = all_text[:4000]


# Step 4: Summarize using OpenAI
def summarize_content(text):
  prompt = f"Summarize the following content in simple terms:\n\n{text}"
  response = client.chat.completions.create(model="gpt-3.5-turbo",
                                            messages=[{
                                                "role": "user",
                                                "content": prompt
                                            }],
                                            temperature=0.5)
  return response.choices[0].message.content


print("\n🧠 Summarizing the research...")
summary = summarize_content(all_text)

# Step 5: Output results
print("\n📘 Summary of Findings:")
print(summary)
