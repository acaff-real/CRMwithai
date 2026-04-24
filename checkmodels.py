import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Error: Could not find GEMINI_API_KEY in your .env file.")
    exit()

client = genai.Client(api_key=api_key)

print("--- AVAILABLE EMBEDDING MODELS ---")
count = 0
for model in client.models.list():
    # We are now looking for embedding models specifically!
    if 'embedContent' in model.supported_actions:
        clean_name = model.name.replace('models/', '')
        print(f"- {clean_name}")
        count += 1

if count == 0:
    print("No embedding models found for this API key.")