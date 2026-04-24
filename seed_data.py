import os
import json
import psycopg2
from dotenv import load_dotenv
from google import genai

# 1. Setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("Error: GEMINI_API_KEY missing.")
    exit()

client = genai.Client(api_key=GEMINI_API_KEY)

# 2. Generate Synthetic Companies
print("1. Asking Gemini to invent 10 synthetic companies...")
prompt = """
Generate exactly 10 synthetic companies. 
Make 5 of them B2B Enterprise Software/SaaS companies (Ideal Clients).
Make 5 of them local brick-and-mortar retail shops (Bad Fit Clients).
Return ONLY a valid JSON array of objects. 
Each object must have these exact keys: "name", "industry", "website", "description".
"""

response = client.models.generate_content(
    model='gemini-flash-latest',
    contents=prompt,
)

# Clean up the response to ensure it's valid JSON
json_string = response.text.strip()
if json_string.startswith("```json"):
    json_string = json_string[7:-3]

companies = json.loads(json_string)
print(f"✅ Generated {len(companies)} companies.")

# 3. Connect to Database
try:
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("\n2. Generating embeddings and saving to database...")
    for company in companies:
        # Create the "Fingerprint" text
        fingerprint = f"{company['name']} is a {company['industry']} company. {company['description']}"
        
        # Ask Gemini to turn the fingerprint into math (Vector Embedding)
        embed_result = client.models.embed_content(
            model='gemini-embedding-2',
            contents=fingerprint,
        )
        
        # Extract the array of 768 numbers
        embedding_values = embed_result.embeddings[0].values
        
        # Format it as a string so PostgreSQL pgvector can read it: "[0.1, 0.2, ...]"
        embedding_str = f"[{','.join(map(str, embedding_values))}]"
        
        # Insert into the database
        cur.execute("""
            INSERT INTO accounts (name, industry, website, embedding)
            VALUES (%s, %s, %s, %s)
        """, (company['name'], company['industry'], company['website'], embedding_str))
        
        print(f"   Saved & Embedded: {company['name']} ({company['industry']})")

    conn.commit()
    cur.close()
    conn.close()
    print("\n✅ Success! Your vector database is now primed and ready.")

except Exception as e:
    print(f"\n❌ Error: {e}")
    if 'conn' in locals(): conn.rollback()