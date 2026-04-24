from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from enum import Enum
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

# NEW: The updated import for the new SDK
from google import genai

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# NEW: Initializing the new Client instead of configuring a global model
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)
else:
    client = None
    print("Warning: GEMINI_API_KEY not found. AI features will be disabled.")

app = FastAPI(title="CRM MVP API")
origins = [
    "http://localhost:3000",  # Standard React app port
    "http://localhost:5173",  # Vite (React/Vue) standard port
    "http://localhost:8000",  # Just in case
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allows all headers
)

# --- PYDANTIC MODELS (Data Validation) ---
class ContactCreate(BaseModel):
    account_id: int
    first_name: str
    last_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    job_title: Optional[str] = None

class DealStage(str, Enum):
    Prospecting = 'Prospecting'
    Discovery = 'Discovery'
    Proposal = 'Proposal'
    Negotiation = 'Negotiation'
    Closed_Won = 'Closed_Won'
    Closed_Lost = 'Closed_Lost'

class DealCreate(BaseModel):
    account_id: int
    contact_id: Optional[int] = None
    title: str
    amount: float = 0.00
    stage: DealStage = DealStage.Prospecting
    probability: int = Field(default=0, ge=0, le=100)

class ActivityType(str, Enum):
    Email = 'Email'
    Call = 'Call'
    Meeting = 'Meeting'
    Note = 'Note'

class AccountCreate(BaseModel):
    name: str
    industry: Optional[str] = None
    website: Optional[str] = None
    owner_id: Optional[int] = None 

class ActivityCreate(BaseModel):
    deal_id: Optional[int] = None
    contact_id: Optional[int] = None
    user_id: Optional[int] = None
    type: ActivityType
    content: str

# --- DATABASE HELPER ---
def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

# --- API ROUTES ---

@app.get("/")
def read_root():
    return {"message": "CRM API is online and running!"}

@app.get("/api/contacts")
def get_contacts():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM contacts;")
        contacts = cur.fetchall()
        
        cur.close()
        conn.close()
        return contacts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/contacts")
def create_contact(contact: ContactCreate):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        insert_query = """
            INSERT INTO contacts (account_id, first_name, last_name, email, phone, job_title)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        cur.execute(insert_query, (
            contact.account_id, contact.first_name, contact.last_name, 
            contact.email, contact.phone, contact.job_title
        ))
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Contact created successfully", "id": new_id}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- DEALS ROUTES ---

@app.get("/api/deals")
def get_deals():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT d.*, a.name as account_name FROM deals d JOIN accounts a ON d.account_id = a.id;")
        deals = cur.fetchall()
        cur.close()
        conn.close()
        return deals
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/deals")
def create_deal(deal: DealCreate):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        insert_query = """
            INSERT INTO deals (account_id, contact_id, title, amount, stage, probability)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        cur.execute(insert_query, (
            deal.account_id, deal.contact_id, deal.title, 
            deal.amount, deal.stage.value, deal.probability
        ))
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Deal created successfully", "id": new_id}
    except Exception as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

class DealStageUpdate(BaseModel):
    stage: DealStage

@app.put("/api/deals/{deal_id}/stage")
def update_deal_stage(deal_id: int, stage_update: DealStageUpdate):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE deals SET stage = %s WHERE id = %s RETURNING id;",
            (stage_update.stage.value, deal_id)
        )
        updated = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        
        if not updated:
            raise HTTPException(status_code=404, detail="Deal not found")
            
        return {"message": "Deal stage updated successfully"}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- ACCOUNTS ROUTES ---

@app.get("/api/accounts")
def get_accounts():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts ORDER BY created_at DESC;")
        accounts = cur.fetchall()
        cur.close()
        conn.close()
        return accounts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/accounts")
def create_account(account: AccountCreate):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        insert_query = """
            INSERT INTO accounts (name, industry, website, owner_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """
        cur.execute(insert_query, (account.name, account.industry, account.website, account.owner_id))
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Account created successfully", "id": new_id}
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- ACTIVITIES ROUTES ---

@app.get("/api/activities")
def get_activities():
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        join_query = """
            SELECT 
                a.id, a.type, a.content, a.sentiment, a.created_at,
                c.first_name, c.last_name,
                d.title as deal_title,
                u.name as rep_name
            FROM activities a
            LEFT JOIN contacts c ON a.contact_id = c.id
            LEFT JOIN deals d ON a.deal_id = d.id
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.created_at DESC;
        """
        cur.execute(join_query)
        activities = cur.fetchall()
        cur.close()
        conn.close()
        return activities
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/activities")
def create_activity(activity: ActivityCreate):
    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    # --- AI INTERCEPTION START ---
    ai_sentiment = "Neutral" 
    
    # NEW: We check 'client' instead of 'model'
    if client and activity.type in [ActivityType.Email, ActivityType.Note]:
        try:
            prompt = f"""
            You are an expert sales assistant analyzing CRM logs. 
            Read the following text and determine the client's sentiment.
            You must respond with EXACTLY ONE of these words: Positive, Neutral, Frustrated, Urgent.
            
            Text: "{activity.content}"
            """
            # NEW: The updated syntax for calling the model using the client
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=prompt,
            )
            ai_sentiment = response.text.strip().capitalize()
            
            if ai_sentiment not in ["Positive", "Neutral", "Frustrated", "Urgent"]:
                ai_sentiment = "Neutral"
                
        except Exception as e:
            print(f"AI Analysis failed: {e}")
            ai_sentiment = "Unanalyzed" 
    # --- AI INTERCEPTION END ---

    try:
        cur = conn.cursor()
        insert_query = """
            INSERT INTO activities (deal_id, contact_id, user_id, type, content, sentiment)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id;
        """
        cur.execute(insert_query, (
            activity.deal_id, 
            activity.contact_id, 
            activity.user_id, 
            activity.type.value, 
            activity.content,
            ai_sentiment 
        ))
        new_id = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        return {
            "message": "Activity logged successfully", 
            "id": new_id,
            "sentiment_detected": ai_sentiment
        }
    except Exception as e:
        if conn: conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

# --- AI COPILOT ROUTES ---

@app.get("/api/deals/{deal_id}/copilot")
def get_deal_copilot_advice(deal_id: int):
    if not client:
        raise HTTPException(status_code=503, detail="AI is not configured.")

    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        cur = conn.cursor()
        
        # 1. Fetch the Deal Information
        cur.execute("SELECT title, amount, stage FROM deals WHERE id = %s;", (deal_id,))
        deal = cur.fetchone()
        
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        # 2. Fetch the History (Activities) for this specific Deal
        cur.execute("""
            SELECT type, content, sentiment, created_at 
            FROM activities 
            WHERE deal_id = %s 
            ORDER BY created_at ASC;
        """, (deal_id,))
        activities = cur.fetchall()
        
        cur.close()
        conn.close()

        # 3. Format the History for the AI
        if not activities:
            return {"advice": "There is no activity history for this deal yet. Reach out and introduce yourself!"}

        history_text = "\n".join([
            f"- [{act['created_at'].strftime('%Y-%m-%d')}] {act['type']}: {act['content']} (Sentiment: {act['sentiment']})" 
            for act in activities
        ])

        # 4. The AI Prompt
        prompt = f"""
        You are an elite B2B sales manager coaching a junior rep.
        Review the following Deal and its interaction history. 
        
        Deal Title: {deal['title']}
        Current Stage: {deal['stage']}
        Value: ${deal['amount']}
        
        Interaction History:
        {history_text}
        
        Based ONLY on this context, provide the single "Next Best Action" the rep should take today to move this deal forward. 
        Keep your advice actionable, highly specific to the history provided, and under 3 sentences.
        """

        # 5. Ask Gemini
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        
        advice = response.text.strip()
        
        return {
            "deal_id": deal_id,
            "ai_advice": advice
        }

    except Exception as e:
        if conn: conn.close()
        raise HTTPException(status_code=500, detail=str(e))

# --- AI LEAD SCORING ROUTE ---

class LeadScoreRequest(BaseModel):
    name: str
    industry: str
    description: str

@app.post("/api/leads/score")
def score_lead(lead: LeadScoreRequest):
    if not client:
        raise HTTPException(status_code=503, detail="AI is not configured.")

    conn = get_db_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    try:
        cur = conn.cursor()

        # 1. Create the fingerprint for the NEW lead
        fingerprint = f"{lead.name} is a {lead.industry} company. {lead.description}"

        # 2. Get the embedding for the new lead using the massive new model
        embed_result = client.models.embed_content(
            model='gemini-embedding-2',
            contents=fingerprint,
        )
        
        # Format the 3072 numbers for PostgreSQL
        embedding_values = embed_result.embeddings[0].values
        embedding_str = f"[{','.join(map(str, embedding_values))}]"

        # 3. Vector Math Magic (Cosine Similarity)
        # The <=> operator calculates distance. 
        # 1 minus distance = similarity score (1.0 is a perfect 100% match)
        query = """
            SELECT 
                name, 
                industry,
                ROUND((1 - (embedding <=> %s::vector))::numeric, 4) AS similarity_score
            FROM accounts
            ORDER BY embedding <=> %s::vector
            LIMIT 3;
        """
        
        # We pass the embedding string twice (once for the SELECT, once for the ORDER BY)
        cur.execute(query, (embedding_str, embedding_str))
        matches = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "lead": lead.name,
            "top_matches": matches
        }

    except Exception as e:
        if conn: conn.close()
        raise HTTPException(status_code=500, detail=str(e))