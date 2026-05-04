# RizzAI — Advanced AI Dating Assistant

RizzAI is a beginner-friendly full-stack project with:

- `frontend/`: Expo React Native app (TypeScript)
- `backend/`: FastAPI API (Python)

## Project Structure

```text
RizzAI/
  frontend/   # Expo + React Native + TypeScript
  backend/    # FastAPI server
```

## Backend Setup (FastAPI)

1. Open a terminal in:
   `c:\Users\Lenovo\Desktop\RizzAI\backend`
2. Create and activate a virtual environment:

   - Windows PowerShell:
     ```powershell
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create env file:

   ```powershell
   Copy-Item .env.example .env
   ```

5. Run the server:

   ```powershell
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

6. Open API docs:
   `http://127.0.0.1:8000/docs`

### Backend Endpoints

- `GET /health` → health check
- `POST /api/reply` → generate reply suggestions

#### `/api/reply` Retrieval Debug Mode (Explainability)

Set `retrieval_debug: true` in the request body to include why patterns were retrieved.

Example request:

```json
{
  "message": "she said lol",
  "tone": "flirty",
  "retrieval_debug": true
}
```

When enabled, response includes `retrieval_debug` items with:

- `pattern_id`
- `tone`
- `situation`
- `score`
- `reason` (short explanation of boosts and ranking signals)

This is useful for your Loom walkthrough because you can show:

1. which examples were used as inspiration,
2. how tone affected ranking,
3. and why the final response is explainable instead of a black box.

### Frontend Explainability Mode (Loom Demo)

The app now includes an **Explainability Mode** toggle in the `Chat Input` screen.

Demo flow for Loom:

1. Enable **Explainability Mode**.
2. Enter a prompt and generate replies.
3. Open the `Reply Results` screen.
4. Expand **Why these suggestions?** to show retrieval details:
   - pattern ID
   - tone
   - situation
   - relevance score
   - ranking reason

When Explainability Mode is off, these debug details stay hidden for a clean user UI.

## RAG Pipeline (LangChain + ChromaDB)

The backend now includes:

- `backend/data/reply_patterns.json` (curated response patterns)
- `backend/scripts/ingest.py` (JSON -> LangChain Documents -> ChromaDB)
- `backend/services/rag_service.py` (retrieval utility)

### RAG Dependencies

Install backend dependencies (already includes LangChain + Chroma):

```powershell
pip install -r requirements.txt
```

### Run Ingestion

From `backend/`:

```powershell
python scripts/ingest.py
```

This will:

- load `data/reply_patterns.json`
- generate embeddings with your OpenAI-compatible provider
- store vectors in `CHROMA_PERSIST_DIR` (default: `./chroma_db`)

To append without deleting old vectors:

```powershell
python scripts/ingest.py --no-reset
```

### Test Retrieval

From `backend/`, run:

```powershell
python -c "from services.rag_service import retrieve_patterns; import json; print(json.dumps(retrieve_patterns('She replied after two days and said hey stranger', 'playful', 5), indent=2))"
```

Expected output: top relevant examples with `id`, `tone`, `situation`, `content`, and `relevance_score`.

## Frontend Setup (Expo React Native)

1. Open a second terminal in:
   `c:\Users\Lenovo\Desktop\RizzAI\frontend`
2. Install dependencies:

   ```powershell
   npm install
   ```

3. Start Expo:

   ```powershell
   npm run start
   ```

4. Open on Android/iOS/Web using the Expo CLI options.

## Notes

- Frontend currently calls the backend at:
  `http://127.0.0.1:8000`
- On a physical phone, update that URL to your computer's local IP in:
  `frontend/src/services/api.ts`
- If `OPENAI_API_KEY` is not set, backend returns demo suggestions so the app still works.
- For RAG ingestion/retrieval, set `OPENAI_API_KEY` in `backend/.env` (plus optional `OPENAI_BASE_URL` for compatible providers).
# RizzAI
