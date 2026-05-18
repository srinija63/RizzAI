# RizzAI (CharmAI)

AI dating assistant — **Expo React Native** frontend + **FastAPI** backend. Generate context-aware replies, profile openers, and bios with optional RAG grounding and ranked suggestions.

## Features

| Screen | What it does |
|--------|----------------|
| **Intro** | Vibrant splash → Get Started |
| **Home** | Hub for all tools |
| **Reply coaching** | Pick **tone** + **confidence** (nothing auto-selected) → paste chat or import screenshot → **3 unique** ranked replies |
| **Opener generator** | Paste their profile → pick tone → first messages grounded in their details |
| **Bio writer** | Your rough notes → pick style template → paste-ready bio variants |

### Reply coaching highlights

- **3 replies** per request — distinct angles, tied to the conversation
- User-chosen **tone**: witty, flirty, bold, direct
- User-chosen **confidence**: soft, balanced, bold
- Optional **Explainability Mode** (retrieval + ranking debug on results)
- Screenshot → text via Gemini vision (`POST /api/extract-from-image`)

## Tech stack

- **Frontend:** Expo 54, React Native, TypeScript, Moti, Tamagui, NativeWind
- **Backend:** FastAPI, Pydantic, LangChain + ChromaDB (RAG)
- **LLM chain:** Gemini → Ollama → mock fallback (app stays usable offline)
- **Embeddings:** Local `sentence-transformers` (no OpenAI key required for RAG)

## Project structure

```text
RizzAI/
  frontend/          # Expo app
    src/screens/     # HeroIntro, Home, ReplySetup, ChatInput, ReplyResults, …
    src/services/    # api.ts — backend client
    assets/          # rizz-logo.png, splash reference
    stitch/          # Stitch design refs + fetch scripts
  backend/
    main.py          # FastAPI entry
    routes/          # chat, analyze, vision, writing, health
    services/        # llm, rizz (RAG), ranking, writing
    data/            # reply_patterns.json
    scripts/ingest.py
```

## Quick start

### 1. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env — set GEMINI_API_KEY for real AI (optional: Ollama for local fallback)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

### 2. RAG ingestion (optional, improves reply quality)

```powershell
cd backend
python scripts/ingest.py
```

Uses `LOCAL_EMBEDDING_MODEL` from `.env` and stores vectors in `./chroma_db`.

### 3. Frontend

```powershell
cd frontend
npm install
npx expo start -c
```

- **Phone:** same Wi‑Fi as PC → scan QR in Expo Go  
- **Stuck connecting?** `npx expo start --tunnel -c`  
- **Web:** press `w` (API uses `http://127.0.0.1:8000`)

Update the fallback LAN IP in `frontend/src/services/api.ts` (`MOBILE_LAN_API_BASE_URL`) if Expo cannot auto-detect your PC.

## Environment variables

Copy `backend/.env.example` → `backend/.env`:

| Variable | Purpose |
|----------|---------|
| `GEMINI_API_KEY` | Primary LLM + screenshot OCR |
| `GEMINI_MODEL` | Default `gemini-2.0-flash` |
| `OLLAMA_BASE_URL` | Local fallback server |
| `OLLAMA_MODELS` | Comma-separated model names |
| `LOCAL_EMBEDDING_MODEL` | RAG embeddings (local) |
| `CHROMA_PERSIST_DIR` | Vector DB path |
| `CHROMA_COLLECTION` | Collection name |

Without `GEMINI_API_KEY`, replies/openers/bios use **Ollama** if running, else **mock** suggestions.

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/reply` | Analyze + RAG + generate + rank **3** replies |
| `POST` | `/api/analyze` | Conversation mood / intent |
| `POST` | `/api/extract-from-image` | Screenshot → conversation text |
| `POST` | `/api/openers` | Profile-grounded first messages |
| `POST` | `/api/bio` | Bio variants from notes + style |

### Example: `/api/reply`

```json
{
  "conversation_text": "Them: lol that was random\nYou: fair",
  "tone": "flirty",
  "confidence_level": "medium",
  "reply_count": 3,
  "retrieval_debug": false
}
```

`tone` and `confidence_level` are **required** (no server-side override). Default `reply_count` is **3** (min 3, max 12).

With `retrieval_debug: true`, the response includes which RAG patterns influenced generation.

## Stitch design assets

Design reference project: **RizzAI Logo Screen** (`17404370540113652731`).

```powershell
cd frontend
$env:STITCH_API_KEY = "your-key-from-stitch.withgoogle.com/settings"
.\scripts\fetch-stitch-via-api.ps1 -ScreenId 048c3380cc92497c9042574ba7528e95 -ScreenSlug rizzai-abstract-logo -AssetName rizz-logo.png
.\scripts\fetch-stitch-via-api.ps1 -ScreenId 4ce103cb2c2c4a209198af8b828a37d1 -ScreenSlug rizzai-vibrant-splash -AssetName rizz-splash-reference.png
```

See `frontend/stitch/DESIGN.md` for screen IDs.

## Explainability demo (Loom / portfolio)

1. Enable **Explainability Mode** on the chat input screen.
2. Generate replies after choosing tone + confidence.
3. On results, expand **Why these suggestions?** to show pattern ID, tone, situation, score, and reason.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Expo cannot reach Metro | Same Wi‑Fi, firewall allows 8081, try `--tunnel` |
| App cannot reach API | Backend on `0.0.0.0:8000`, correct LAN IP in `api.ts` |
| Slow first reply | First run loads embedding model + LLM; wait or use Gemini |
| Generic / repeated replies | Set `GEMINI_API_KEY`; restart backend after `.env` changes |
| Openers ignore profile | Paste full profile text; pick tone before generate |

## License

Private / educational project — adjust as needed for your use case.
