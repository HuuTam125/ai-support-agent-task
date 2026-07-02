"""
Converts Zendesk article HTML body into clean Markdown files.
Preserves headings, code blocks, and relative/absolute links.
Strips nav/ads by relying on the fact that Zendesk API 'body' field
already contains only the article content (no site nav/footer).
"""

import os
import re
import html2text


def slugify(title: str) -> str:
    slug = title.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "untitled"


def build_markdown_converter() -> html2text.HTML2Text:
    converter = html2text.HTML2Text()
    converter.body_width = 0          # don't hard-wrap lines
    converter.ignore_images = False
    converter.ignore_links = False    # keep relative + absolute links
    converter.mark_code = True
    converter.protect_links = True
    return converter


def article_to_markdown(article: dict) -> str:
    """
    Builds a markdown document for one Zendesk article, including
    a small frontmatter-like header with metadata + Article URL line
    (needed later so Gemini can cite 'Article URL:' per the system prompt).
    """
    converter = build_markdown_converter()
    body_md = converter.handle(article.get("body") or "")

    header = (
        f"# {article['title']}\n\n"
        f"Article URL: {article['html_url']}\n"
        f"Last Updated: {article.get('updated_at', '')}\n\n"
        "---\n\n"
    )
    return header + body_md.strip() + "\n"


def save_article_markdown(article: dict, output_dir: str = "data/articles") -> str:
    os.makedirs(output_dir, exist_ok=True)
    slug = slugify(article["title"])
    filepath = os.path.join(output_dir, f"{slug}.md")

    md_content = article_to_markdown(article)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)

    return filepath


if __name__ == "__main__":
    from src.zendesk_client import fetch_articles

    articles = fetch_articles()
    print(f"Fetched {len(articles)} articles. Converting to Markdown...")

    saved = 0
    for art in articles:
        path = save_article_markdown(art)
        saved += 1

    print(f"Saved {saved} markdown files to data/articles/")