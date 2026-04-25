"""
analyzer.py — AI analysis engine for NewsEyeNewsEye
Uses Ollama to analyze emotion, urgency, affected groups and public reaction
"""
import json
import ollama
from config import OLLAMA_MODEL, EMOTIONS, URGENCY_LEVELS, TOPICS
from database import get_unanalyzed_articles, update_analysis

# ── Analysis Prompt ────────────────────────────────────────────────────────────
def build_prompt(title, summary):
    return f"""You are a professional news intelligence analyst. Analyze this news article and respond ONLY with a valid JSON object — no explanation, no markdown, no extra text.

Article Title: {title}
Article Summary: {summary}

Respond with exactly this JSON structure:
{{
    "emotion": "one of: Fear, Anger, Hope, Sadness, Excitement, Neutral",
    "emotion_scores": {{
        "Fear": 0.0,
        "Anger": 0.0,
        "Hope": 0.0,
        "Sadness": 0.0,
        "Excitement": 0.0,
        "Neutral": 0.0
    }},
    "urgency": "one of: Breaking, Developing, Background",
    "topic": "one of: Politics, War & Conflict, Economy, Sports, Technology, Science, Culture, Health, Environment, Crime",
    "affected_groups": ["list", "of", "affected", "groups", "or", "communities"],
    "public_reaction": "one sentence describing how the public is likely to react to this news"
}}

Rules:
- emotion_scores must sum to 1.0
- emotion must match the highest emotion_score
- affected_groups should be specific 
- public_reaction should be realistic and specific
- respond with JSON only, nothing else
"""

# ── Parse AI Response ──────────────────────────────────────────────────────────
def parse_response(response_text):
    """Extract and validate JSON from AI response."""
    try:
        # Clean response — remove markdown if model adds it
        text = response_text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)

        # Validate required fields
        required = ["emotion", "emotion_scores", "urgency",
                   "topic", "affected_groups", "public_reaction"]
        for field in required:
            if field not in data:
                data[field] = get_default(field)

        # Validate emotion is valid
        if data["emotion"] not in EMOTIONS:
            data["emotion"] = "Neutral"

        # Validate urgency is valid
        if data["urgency"] not in URGENCY_LEVELS:
            data["urgency"] = "Background"

        # Validate topic is valid
        if data["topic"] not in TOPICS:
            data["topic"] = "Politics"

        # Ensure affected_groups is a list
        if not isinstance(data["affected_groups"], list):
            data["affected_groups"] = []

        return data

    except Exception as e:
        print(f"  Parse error: {e}")
        return get_default_analysis()

def get_default(field):
    defaults = {
        "emotion":        "Neutral",
        "emotion_scores": {"Fear":0,"Anger":0,"Hope":0,
                          "Sadness":0,"Excitement":0,"Neutral":1.0},
        "urgency":        "Background",
        "topic":          "Politics",
        "affected_groups":[],
        "public_reaction":"No reaction data available",
    }
    return defaults.get(field, "")

def get_default_analysis():
    return {
        "emotion":        "Neutral",
        "emotion_scores": {"Fear":0,"Anger":0,"Hope":0,
                          "Sadness":0,"Excitement":0,"Neutral":1.0},
        "urgency":        "Background",
        "topic":          "Politics",
        "affected_groups":[],
        "public_reaction":"Analysis unavailable",
    }

# ── Analyze Single Article ─────────────────────────────────────────────────────
def analyze_article(article):
    """
    Send one article to Ollama for analysis.
    Returns analysis dict.
    """
    title   = article.get("title", "")
    summary = article.get("summary", "")

    if not title:
        return get_default_analysis()

    try:
        prompt   = build_prompt(title, summary)
        response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response["message"]["content"]
        return parse_response(raw)

    except Exception as e:
        print(f"  Ollama error: {e}")
        return get_default_analysis()

# ── Analyze Batch ──────────────────────────────────────────────────────────────
def analyze_pending(batch_size=5, on_progress=None):
    """
    Analyze all unanalyzed articles in batches.
    AP and Reuters articles are prioritized automatically by database query.
    """
    articles = get_unanalyzed_articles(limit=batch_size)

    if not articles:
        print("No articles pending analysis")
        return 0

    print(f"\n{'='*50}")
    print(f"Analyzing {len(articles)} articles...")
    print(f"{'='*50}")

    count = 0
    for article in articles:
        title = article["title"][:60]
        print(f"\n◈ [{article['source']}] {title}...")

        if on_progress:
            on_progress(f"Analyzing: {title[:40]}...")

        analysis = analyze_article(article)

        print(f"  Emotion:  {analysis['emotion']}")
        print(f"  Urgency:  {analysis['urgency']}")
        print(f"  Topic:    {analysis['topic']}")
        print(f"  Affected: {', '.join(analysis['affected_groups'][:3])}")

        update_analysis(article["id"], analysis)
        count += 1

    print(f"\n✅ Analyzed {count} articles")
    return count

# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from database import initialize_db
    initialize_db()

    # Test with one article
    test = {
        "title":   "Gaza ceasefire talks collapse as violence escalates",
        "summary": "Negotiations between Israel and Hamas have broken down as fighting intensifies in the Gaza Strip, with international mediators expressing deep concern.",
    }

    print("Testing analyzer with sample article...")
    result = analyze_article(test)
    print(json.dumps(result, indent=2))

    # Analyze real pending articles
    print("\nAnalyzing pending articles from database...")
    analyze_pending(batch_size=3)