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

    print("Step 4: Uploading changed files to Gemini File API...")
    
    client = get_gemini_client()
    
    uploaded = []
    for path in changed_paths:
        try:
            filename = os.path.basename(path)
            
            gfile = client.files.upload(
                file=path,
                config={
                    "mime_type": "text/markdown",
                    "display_name": filename
                }
            )
            uploaded.append(gfile)
            print(f"  Uploaded: {path} -> {gfile.name}")
        except Exception as e:
            print(f"  FAILED: {path} ({e})")
    print(f"  ✅ Uploaded {len(uploaded)}/{len(changed_paths)} changed files.\n")

    print("Step 5: Saving updated sync_state.json...")
    save_state(new_state)
    print("  Done.\n")

    print("=== Sync complete ===")
    print(f"Summary: added={counts['added']} updated={counts['updated']} skipped={counts['skipped']}")


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: Job failed: {e}", file=sys.stderr)
        sys.exit(1)