"""
database.py — SQLite database engine for NewsEyeNewsEye
Handles all data storage and retrieval
"""
import sqlite3
import json
from datetime import datetime
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            title           TEXT NOT NULL,
            summary         TEXT,
            url             TEXT UNIQUE,
            source          TEXT,
            published       TEXT,
            collected_at    TEXT,
            emotion         TEXT,
            emotion_scores  TEXT,
            urgency         TEXT,
            topic           TEXT,
            credibility     INTEGER,
            affected_groups TEXT,
            public_reaction TEXT,
            analyzed        INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT UNIQUE,
            url             TEXT,
            credibility     INTEGER,
            total_articles  INTEGER DEFAULT 0,
            last_fetched    TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_stats (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             TEXT UNIQUE,
            total_articles   INTEGER DEFAULT 0,
            dominant_emotion TEXT,
            dominant_topic   TEXT,
            breaking_count   INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized successfully")

# ── Article Operations ─────────────────────────────────────────────────────────
def insert_article(article):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT OR IGNORE INTO articles
            (title, summary, url, source, published, collected_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            article.get("title", ""),
            article.get("summary", ""),
            article.get("url", ""),
            article.get("source", ""),
            article.get("published", ""),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        conn.commit()
    except Exception as e:
        print(f"Insert error: {e}")
    finally:
        conn.close()

def update_analysis(article_id, analysis):
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE articles SET
                emotion         = ?,
                emotion_scores  = ?,
                urgency         = ?,
                topic           = ?,
                affected_groups = ?,
                public_reaction = ?,
                analyzed        = 1
            WHERE id = ?
        """, (
            analysis.get("emotion", "Neutral"),
            json.dumps(analysis.get("emotion_scores", {})),
            analysis.get("urgency", "Background"),
            analysis.get("topic", "General"),
            json.dumps(analysis.get("affected_groups", [])),
            analysis.get("public_reaction", ""),
            article_id,
        ))
        conn.commit()
    except Exception as e:
        print(f"Update error: {e}")
    finally:
        conn.close()

def get_recent_articles(limit=50, analyzed_only=False):
    conn = get_connection()
    try:
        query = """
            SELECT * FROM articles
            {}
            ORDER BY collected_at DESC
            LIMIT ?
        """.format("WHERE analyzed = 1" if analyzed_only else "")
        rows = conn.execute(query, (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_unanalyzed_articles(limit=10):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT * FROM articles
            WHERE analyzed = 0
            ORDER BY
                CASE source
                    WHEN 'AP News' THEN 1
                    WHEN 'Reuters' THEN 2
                    ELSE 3
                END,
                collected_at DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_stats():
    conn = get_connection()
    try:
        total    = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
        analyzed = conn.execute("SELECT COUNT(*) FROM articles WHERE analyzed=1").fetchone()[0]
        breaking = conn.execute("SELECT COUNT(*) FROM articles WHERE urgency='Breaking'").fetchone()[0]
        today    = datetime.now().strftime("%Y-%m-%d")
        today_count = conn.execute(
            "SELECT COUNT(*) FROM articles WHERE collected_at LIKE ?",
            (f"{today}%",)).fetchone()[0]
        emotion_row = conn.execute("""
            SELECT emotion, COUNT(*) as count FROM articles
            WHERE analyzed=1 AND collected_at LIKE ?
            GROUP BY emotion ORDER BY count DESC LIMIT 1
        """, (f"{today}%",)).fetchone()
        topic_row = conn.execute("""
            SELECT topic, COUNT(*) as count FROM articles
            WHERE analyzed=1 AND collected_at LIKE ?
            GROUP BY topic ORDER BY count DESC LIMIT 1
        """, (f"{today}%",)).fetchone()
        return {
            "total":            total,
            "analyzed":         analyzed,
            "breaking":         breaking,
            "today":            today_count,
            "dominant_emotion": emotion_row[0] if emotion_row else "N/A",
            "dominant_topic":   topic_row[0]   if topic_row   else "N/A",
        }
    finally:
        conn.close()

def get_emotion_distribution(days=1):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT emotion, COUNT(*) as count FROM articles
            WHERE analyzed=1 AND collected_at >= datetime('now', ?)
            GROUP BY emotion ORDER BY count DESC
        """, (f"-{days} days",)).fetchall()
        return {row["emotion"]: row["count"] for row in rows}
    finally:
        conn.close()

def get_topic_distribution(days=1):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT topic, COUNT(*) as count FROM articles
            WHERE analyzed=1 AND collected_at >= datetime('now', ?)
            GROUP BY topic ORDER BY count DESC
        """, (f"-{days} days",)).fetchall()
        return {row["topic"]: row["count"] for row in rows}
    finally:
        conn.close()

def get_affected_groups(days=1):
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT affected_groups FROM articles
            WHERE analyzed=1 AND affected_groups IS NOT NULL
            AND collected_at >= datetime('now', ?)
        """, (f"-{days} days",)).fetchall()
        counts = {}
        for row in rows:
            try:
                groups = json.loads(row["affected_groups"])
                for g in groups:
                    counts[g] = counts.get(g, 0) + 1
            except:
                pass
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10])
    finally:
        conn.close()

def search_articles(keyword="", source="", topic="",
                    emotion="", urgency="", limit=50):
    conn = get_connection()
    try:
        conditions = ["analyzed = 1"]
        params     = []
        if keyword:
            conditions.append("(title LIKE ? OR summary LIKE ?)")
            params += [f"%{keyword}%", f"%{keyword}%"]
        if source:
            conditions.append("source = ?")
            params.append(source)
        if topic:
            conditions.append("topic = ?")
            params.append(topic)
        if emotion:
            conditions.append("emotion = ?")
            params.append(emotion)
        if urgency:
            conditions.append("urgency = ?")
            params.append(urgency)
        query = f"""
            SELECT * FROM articles
            WHERE {' AND '.join(conditions)}
            ORDER BY collected_at DESC LIMIT ?
        """
        params.append(limit)
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def clear_old_articles(keep=5000):
    conn = get_connection()
    try:
        conn.execute("""
            DELETE FROM articles WHERE id NOT IN (
                SELECT id FROM articles ORDER BY collected_at DESC LIMIT ?
            )
        """, (keep,))
        conn.commit()
    finally:
        conn.close()

# ── Trend Functions ────────────────────────────────────────────────────────────
def get_keyword_trend(keyword, days=7):
    """Count articles mentioning keyword per day for last N days."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT DATE(collected_at) as day, COUNT(*) as count
            FROM articles
            WHERE (title LIKE ? OR summary LIKE ?)
            AND collected_at >= datetime('now', ?)
            GROUP BY DATE(collected_at)
            ORDER BY day ASC
        """, (f"%{keyword}%", f"%{keyword}%", f"-{days} days")).fetchall()
        return {row["day"]: row["count"] for row in rows}
    finally:
        conn.close()

def get_emotion_trend(days=7):
    """Get emotion distribution per day for last N days."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT DATE(collected_at) as day, emotion, COUNT(*) as count
            FROM articles
            WHERE analyzed=1 AND collected_at >= datetime('now', ?)
            GROUP BY DATE(collected_at), emotion
            ORDER BY day ASC
        """, (f"-{days} days",)).fetchall()
        result = {}
        for row in rows:
            day = row["day"]
            if day not in result:
                result[day] = {}
            result[day][row["emotion"]] = row["count"]
        return result
    finally:
        conn.close()

def get_topic_trend(days=7):
    """Get topic distribution per day for last N days."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT DATE(collected_at) as day, topic, COUNT(*) as count
            FROM articles
            WHERE analyzed=1 AND collected_at >= datetime('now', ?)
            GROUP BY DATE(collected_at), topic
            ORDER BY day ASC
        """, (f"-{days} days",)).fetchall()
        result = {}
        for row in rows:
            day = row["day"]
            if day not in result:
                result[day] = {}
            result[day][row["topic"]] = row["count"]
        return result
    finally:
        conn.close()

def get_trending_keywords(days=1, limit=10):
    """
    Find keywords rising most compared to previous period.
    Returns list of (keyword, today_count, change_pct)
    """
    import re
    from collections import Counter
    conn = get_connection()
    try:
        STOP = {
            "the","a","an","in","on","at","to","for","of","and","or",
            "but","is","are","was","were","has","have","had","with",
            "as","by","from","that","this","it","its","not","be",
            "will","can","would","could","should","may","might",
            "about","over","after","before","between","through",
            "says","say","said","report","reports","new","after",
            "into","than","more","their","they","who","what","how",
            "reuters","jazeera","times","news","post","guardian",
            "also","just","some","been","when","where","which","while",
        }

        def extract_words(rows):
            counter = Counter()
            for row in rows:
                words = re.findall(r'\b[a-zA-Z]{4,}\b', row[0].lower())
                counter.update(w for w in words if w not in STOP)
            return counter

        today = conn.execute("""
            SELECT title FROM articles
            WHERE collected_at >= datetime('now', '-1 days')
        """).fetchall()

        yesterday = conn.execute("""
            SELECT title FROM articles
            WHERE collected_at >= datetime('now', '-2 days')
            AND collected_at < datetime('now', '-1 days')
        """).fetchall()

        today_counts     = extract_words(today)
        yesterday_counts = extract_words(yesterday)

        trends = []
        for word, count in today_counts.most_common(50):
            if count < 3: continue
            prev   = yesterday_counts.get(word, 0)
            change = ((count - prev) / prev * 100) if prev > 0 else 100.0
            trends.append((word.capitalize(), count, change))

        trends.sort(key=lambda x: x[2], reverse=True)
        return trends[:limit]
    finally:
        conn.close()

def get_breaking_trend(days=7):
    """Count breaking news articles per day."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT DATE(collected_at) as day, COUNT(*) as count
            FROM articles
            WHERE urgency='Breaking'
            AND collected_at >= datetime('now', ?)
            GROUP BY DATE(collected_at)
            ORDER BY day ASC
        """, (f"-{days} days",)).fetchall()
        return {row["day"]: row["count"] for row in rows}
    finally:
        conn.close()

# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    initialize_db()
    print("Stats:", get_stats())
    print("Trending keywords:", get_trending_keywords())