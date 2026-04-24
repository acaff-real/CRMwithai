AI-Powered CRM BackendA blazing-fast, intelligent CRM backend built with FastAPI, PostgreSQL (Neon), and the Google Gemini API.This isn't just a database; it's an active sales engine. It features real-time sentiment analysis, a context-aware AI Sales Copilot, and semantic lead scoring using vector embeddings.Key AI FeaturesLive Sentiment Analysis: Automatically analyzes incoming emails and call notes to tag client sentiment (Positive, Neutral, Frustrated, Urgent) using gemini-flash-latest.Sales Copilot: Evaluates entire deal histories to provide actionable "Next Best Action" advice for sales reps.Semantic Lead Scoring: Uses gemini-embedding-2 and PostgreSQL pgvector to create 3072-dimensional mathematical fingerprints of companies, matching new leads to your ideal customer profiles via Cosine Similarity.Tech StackFramework: FastAPI (Python)Database: PostgreSQL (Hosted via Neon serverless)Vector Engine: pgvector extensionAI SDK: google-genaiValidation: PydanticSetup & Installation1. Clone and enter the directorycd crm-backend

2. Create and activate a virtual environmentpython -m venv venv
# On Windows:
```
venv\Scripts\activate
```
# On Mac/Linux:
```
source venv/bin/activate
```
3. Install dependenciespip install fastapi uvicorn pydantic psycopg2-binary python-dotenv google-genai

4. Environment Variables: Create a .env file in the root directory and add your credentials:
DATABASE_URL="postgresql://user:password@your-neon-hostname.neon.tech/dbname?sslmode=require"
GEMINI_API_KEY="your_google_gemini_api_key"

5. Database Initialization: Ensure your PostgreSQL database has the pgvector extension enabled and the proper schema configured:CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE accounts ADD COLUMN embedding VECTOR(3072);

(Run seed_data.py to generate synthetic companies and their embeddings).Running the ServerStart the FastAPI development server with Uvicorn:uvicorn main:app --reload

The API will be available at http://localhost:8000.Interactive Swagger API documentation is automatically generated at http://localhost:8000/docs.Core API RoutesGET /api/deals - Fetch pipeline data.PUT /api/deals/{id}/stage - Update Kanban stage.POST /api/activities - Log calls/emails (Triggers auto-sentiment analysis).GET /api/deals/{id}/copilot - Ask Gemini for the Next Best Action on a deal.POST /api/leads/score - Run vector similarity search against a new lead.
