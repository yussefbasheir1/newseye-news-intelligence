# NewsEye — News Intelligence Dashboard

An AI-powered desktop application that continuously collects news from global 
sources, analyzes sentiment and urgency using a local LLM, and presents 
intelligence-grade insights through an interactive dashboard.

## Features
- Collects articles from 10+ global news sources via RSS feeds
- AI analysis using locally-running LLM (llama3.2 via Ollama) — zero cloud dependency
- Classifies each article by emotion, urgency, topic, affected groups, and predicted public reaction
- 7-tab dashboard: Live Feed, Emotions, Topics, Affected Groups, Search, Sources, Trends
- Trending keyword detection and 7-day trend analysis
- Full-text search with filters
- Source credibility scoring system
- Background threading for non-blocking UI

## Tech Stack
- Python
- CustomTkinter — desktop UI
- Ollama (llama3.2) — local AI analysis
- SQLite — local database
- Matplotlib — charts and visualizations
- feedparser — RSS collection
- Selenium — OSINT scraping

## Requirements
1. Install Python 3.10+
2. Install and run Ollama: https://ollama.ai
3. Pull the model: `ollama pull llama3.2`
4. Install dependencies: `pip install -r requirements.txt`
5. Run: `python main.py`

## Notes
- All AI processing runs locally — no API keys or cloud services required
- Ollama must be running before launching the app
