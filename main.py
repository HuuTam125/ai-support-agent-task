"""
OptiBot Mini-Clone - Daily Sync Job
Entry point: scrapes Zendesk articles, converts to markdown, uploads only
the delta to Gemini File API, and logs added/updated/skipped counts.

Run: python main.py
Exits 0 on success (required for Docker/GitHub Actions).
"""

import sys
import os
from dotenv import load_dotenv

from src.zendesk_client import fetch_articles
from src.html_to_markdown import save_article_markdown
from src.delta_sync import load_state, save_state, compute_delta
from src.gemini_client import get_gemini_client

load_dotenv()  # no-op in GitHub Actions (env vars come from Secrets), useful locally

def main():
    print("=== OptiBot Mini-Clone: Daily Sync Job ===\n")

    print("Step 1: Fetching articles from Zendesk...")
    articles = fetch_articles()
    print(f"  Fetched {len(articles)} articles.\n")

    print("Step 2: Computing delta against sync_state.json...")
    state = load_state()
    to_process, new_state, counts = compute_delta(articles, state)
    print(f"  added={counts['added']}  updated={counts['updated']}  skipped={counts['skipped']}\n")

    if not to_process:
        print("No changes detected. Nothing to upload today. Exiting.")
        save_state(new_state)
        return

    print(f"Step 3: Converting {len(to_process)} changed article(s) to Markdown...")
    changed_paths = []
    for art in to_process:
        path = save_article_markdown(art)
        changed_paths.append(path)
    print(f"  Saved {len(changed_paths)} markdown files.\n")

    print("Step 4: Chunking + embedding changed articles into vector store...")
    from src.vector_store import (
        load_store, save_store, remove_article_chunks, embed_article,
    )

    store = load_store()
    total_new_chunks = 0

    for art, path in zip(to_process, changed_paths):
        article_id = str(art["id"])
        with open(path, "r", encoding="utf-8") as f:
            md_text = f.read()

        # drop stale chunks if this article was previously embedded (update case)
        store = remove_article_chunks(store, article_id)

        records = embed_article(
            article_id=article_id,
            slug=os.path.basename(path).replace(".md", ""),
            article_url=art["html_url"],
            markdown_text=md_text,
        )
        store.extend(records)
        total_new_chunks += len(records)
        print(f"  Embedded {len(records)} chunk(s) for: {art['title']}")

    save_store(store)
    print(f"\n  ✅ Embedded {len(to_process)} file(s), {total_new_chunks} chunk(s) this run.")
    print(f"  📦 Vector store now holds {len(store)} total chunks across all articles.\n")

if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Job failed: {e}", file=sys.stderr)
        sys.exit(1)