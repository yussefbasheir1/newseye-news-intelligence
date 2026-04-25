# ── NewsEye Configuration ────────────────────────────────────────────────────────

# ── Database ───────────────────────────────────────────────────────────────────
DB_PATH = "data/pulse.db"

# ── News Sources ───────────────────────────────────────────────────────────────
# Priority sources — analyzed first
PRIORITY_SOURCES = {
    "AP News":  "https://news.google.com/rss/search?q=AP+News+world&hl=en-US&gl=US&ceid=US:en",
    "Reuters":  "https://news.google.com/rss/search?q=reuters+world+news&hl=en-US&gl=US&ceid=US:en",
}

# Secondary sources
SECONDARY_SOURCES = {
    "BBC News":          "https://feeds.bbci.co.uk/news/rss.xml",
    "Al Jazeera":        "https://news.google.com/rss/search?q=when:24h+allinurl:aljazeera.com&ceid=US:en&hl=en-US&gl=US",
    "The Guardian":      "https://www.theguardian.com/world/rss",
    "France 24":         "https://www.france24.com/en/rss",
    "DW":                "https://rss.dw.com/rdf/rss-en-all",
    "NY Times":          "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    "South China Morning Post": "https://www.scmp.com/rss/5/feed",
    "Egypt Independent": "https://www.egyptindependent.com/feed/",
}

# All sources combined — priority first
ALL_SOURCES = {**PRIORITY_SOURCES, **SECONDARY_SOURCES}

# ── Collection Settings ────────────────────────────────────────────────────────
REFRESH_INTERVAL_MINUTES = 15
MAX_ARTICLES_PER_SOURCE  = 30
MAX_ARTICLES_STORED      = 5000

# ── Source Credibility Scores (0-100) ──────────────────────────────────────────
SOURCE_CREDIBILITY = {
    "AP News":          95,
    "Reuters":          95,
    "BBC News":         90,
    "NY Times":         88,
    "The Guardian":     85,
    "DW":               83,
    "Al Jazeera":       82,
    "France 24":        80,
    "South China Morning Post": 82,
    "Egypt Independent":  70,

}

# ── Emotion Categories ─────────────────────────────────────────────────────────
EMOTIONS = ["Fear", "Anger", "Hope", "Sadness", "Excitement", "Neutral"]

# ── Urgency Levels ─────────────────────────────────────────────────────────────
URGENCY_LEVELS = ["Breaking", "Developing", "Background"]

# ── Topic Categories ───────────────────────────────────────────────────────────
TOPICS = [
    "Politics", "War & Conflict", "Economy",
    "Sports", "Technology", "Science",
    "Culture", "Health", "Environment", "Crime"
]

# ── AI Model ───────────────────────────────────────────────────────────────────
OLLAMA_MODEL = "llama3.2"

# ── UI Colors ──────────────────────────────────────────────────────────────────
BG          = "#0a0e1a"
BG_PANEL    = "#111827"
BG_CARD     = "#1a2235"
BORDER      = "#1e2d42"
ACCENT      = "#00d4ff"
GREEN       = "#00cc66"
PINK        = "#e94560"
ORANGE      = "#ff9944"
PURPLE      = "#aa88ff"
YELLOW      = "#ffd700"
RED         = "#ff4444"
TEXT        = "#e8eaf0"
DIM         = "#8892a4"

# ── Emotion Colors ─────────────────────────────────────────────────────────────
EMOTION_COLORS = {
    "Fear":       "#ff4444",
    "Anger":      "#ff6600",
    "Hope":       "#00cc66",
    "Sadness":    "#6699ff",
    "Excitement": "#ffd700",
    "Neutral":    "#8892a4",
}

# ── Urgency Colors ─────────────────────────────────────────────────────────────
URGENCY_COLORS = {
    "Breaking":   "#ff4444",
    "Developing": "#ff9944",
    "Background": "#8892a4",
}