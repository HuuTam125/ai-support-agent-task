# AI Support Agent Task

A lightweight AI support-bot pipeline: scrapes Help Center articles, converts
them to Markdown, and syncs the delta to Google Gemini as a knowledge base for
a support-assistant bot ("OptiBot"-style), running fully free via GitHub
Actions.

## Project Structure
```text
├── main.py                    # Entry point: full sync workflow, exits 0 on success
├── src/
│   ├── zendesk_client.py      # Fetches articles via Help Center API (paginated)
│   ├── html_to_markdown.py    # Converts article HTML -> clean <slug>.md
│   ├── gemini_client.py       # Uploads files to Gemini File API + chat w/ system prompt
│   └── delta_sync.py          # Compares updated_at vs sync_state.json
├── data/articles/             # Generated markdown files (git-ignored)
├── sync_state.json            # Tracks last-seen updated_at per article id
├── Dockerfile
├── .github/workflows/daily-sync.yml
└── .env.sample
```
## Knowledge Base Approach (Gemini File API)
Gemini's Free Tier has no managed vector-store product like OpenAI's. Instead,
each Markdown article is uploaded individually via `genai.upload_file()`
(Gemini File API). At query time, the relevant uploaded file objects are
passed directly into `generate_content()` alongside the user's question, so
the model reads the full article content as grounding context — a simple
retrieval-free equivalent of a vector store, at zero cost.

Trade-off: this doesn't do semantic chunking/embedding search like a real
vector store — it relies on passing full documents. It's adequate at this
article count; for larger corpora, true embeddings (e.g. `text-embedding-004`
+ a local FAISS index) would be the next step. Files also auto-expire after
48h on Gemini's side, which is why the daily job re-uploads only the delta
each run rather than relying on a persistent store.

Chunking: not applied — each article is uploaded as one whole file (articles
are short enough that whole-document grounding fits within context).

## Delta Sync Logic
Each article's `updated_at` (from the Zendesk API) is compared against the
last-seen value stored in `sync_state.json`:
- Not in state → **added**
- Present but timestamp changed → **updated**
- Present and unchanged → **skipped**

Only added/updated articles are re-converted and re-uploaded. Counts are
logged to console every run.

## Knowledge Base Approach (Local Vector Store via Gemini Embeddings)
Gemini's Free Tier has no managed vector-store product like OpenAI's, so we
built a minimal equivalent:
1. Each markdown article is split into ~800-char chunks with 100-char overlap
   (paragraph-aware sliding window, `src/vector_store.py`).
2. Each chunk is embedded via Gemini's Embedding API (`text-embedding-004`).
3. Chunks + embeddings + metadata (article URL, slug) are persisted to
   `data/vector_store.json` — our local vector store.
4. At query time, the question is embedded and compared via cosine
   similarity against all stored chunks; the top-3 most relevant chunks are
   passed to `gemini-2.0-flash` as grounding context, along with the strict
   system instruction.

Only chunks belonging to added/updated articles are re-embedded on each
daily run (delta sync); unchanged articles' chunks are left untouched in
the store. Each run logs: files processed, chunks newly embedded, and total
chunks in the store.

## Run Locally
```bash
git clone <this-repo>
cd ai-support-agent-task
cp .env.sample .env        # fill in GEMINI_API_KEY
pip install -r requirements.txt
python main.py
```

## Run with Docker
```bash
docker build -t ai-support-agent-task .
docker run -e GEMINI_API_KEY=your_key ai-support-agent-task
# exits 0 on success, 1 on failure
```

## Daily Job (GitHub Actions)
Runs once/day (cron `0 3 * * *`, UTC) via `.github/workflows/daily-sync.yml`,
builds the Docker image, runs the sync, and commits the updated
`sync_state.json`. Requires a repo secret `GEMINI_API_KEY`.

👉 View logs: **repo → Actions tab → "Daily OptiBot Sync"**
(can also be triggered manually via `workflow_dispatch`)
