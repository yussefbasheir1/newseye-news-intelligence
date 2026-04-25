"""
collector.py — News collection engine for NewsEyeNewsEye
Fetches articles from RSS feeds — AP and Reuters first
"""
import feedparser
import requests
from datetime import datetime
from config import ALL_SOURCES, PRIORITY_SOURCES, MAX_ARTICLES_PER_SOURCE, SOURCE_CREDIBILITY
from database import insert_article, clear_old_articles

def parse_date(entry):
    """Extract published date from RSS entry."""
    for field in ["published", "updated", "created"]:
        if hasattr(entry, field):
            return getattr(entry, field)
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def clean_text(text):
    """Remove HTML tags, HTML entities and extra whitespace."""
    import re
    if not text: return ""
    text = re.sub(r'<[^>]+>', '', text)       # Remove HTML tags
    text = text.replace('&nbsp;', ' ')         # Fix &nbsp;
    text = text.replace('&amp;', '&')          # Fix &amp;
    text = text.replace('&lt;', '<')           # Fix &lt;
    text = text.replace('&gt;', '>')           # Fix &gt;
    text = text.replace('&quot;', '"')         # Fix &quot;
    text = re.sub(r'&[a-zA-Z]+;', '', text)   # Remove remaining entities
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]

def fetch_source(source_name, rss_url, on_progress=None):
    """
    Fetch articles from a single RSS feed.
    Returns list of article dicts.
    """
    articles = []
    try:
        if on_progress:
            on_progress(f"Fetching {source_name}...")

        # Parse RSS feed
        feed = feedparser.parse(rss_url)

        if feed.bozo and not feed.entries:
            print(f"  ⚠ {source_name}: Feed error — {feed.bozo_exception}")
            return []

        for entry in feed.entries[:MAX_ARTICLES_PER_SOURCE]:
            # Get summary — try multiple fields
            summary = ""
            if hasattr(entry, "summary"):
                summary = clean_text(entry.summary)
            elif hasattr(entry, "description"):
                summary = clean_text(entry.description)
            elif hasattr(entry, "content"):
                summary = clean_text(entry.content[0].value)

            article = {
                "title":     clean_text(entry.get("title", "")),
                "summary":   summary,
                "url":       entry.get("link", ""),
                "source":    source_name,
                "published": parse_date(entry),
                "credibility": SOURCE_CREDIBILITY.get(source_name, 70),
            }

            # Skip articles with no title or url
            if not article["title"] or not article["url"]:
                continue

            articles.append(article)

        print(f"  ✓ {source_name}: {len(articles)} articles fetched")
        return articles

    except Exception as e:
        print(f"  ✗ {source_name}: {e}")
        return []

def collect_all(on_progress=None):
    """
    Collect from all sources — priority sources first.
    Returns total number of new articles inserted.
    """
    print(f"\n{'='*50}")
    print(f"Collection started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*50}")

    total_new = 0

    # ── Priority sources first (AP, Reuters) ──────────────────────────────────
    print("\n◈ Priority Sources:")
    for name, url in PRIORITY_SOURCES.items():
        articles = fetch_source(name, url, on_progress)
        for article in articles:
            insert_article(article)
            total_new += 1

    # ── Secondary sources ──────────────────────────────────────────────────────
    secondary = {k: v for k, v in ALL_SOURCES.items()
                 if k not in PRIORITY_SOURCES}
    print("\n◈ Secondary Sources:")
    for name, url in secondary.items():
        articles = fetch_source(name, url, on_progress)
        for article in articles:
            insert_article(article)
            total_new += 1

    # ── Cleanup old articles ───────────────────────────────────────────────────
    clear_old_articles()

    print(f"\n✅ Collection complete — {total_new} articles processed")
    print(f"{'='*50}\n")
    return total_new

# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from database import initialize_db, get_stats
    initialize_db()
    collect_all()
    stats = get_stats()
    print(f"Database now has {stats['total']} articles")