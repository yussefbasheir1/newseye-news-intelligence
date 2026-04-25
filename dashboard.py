"""
dashboard.py — Main UI for NewsEye News Intelligence Dashboard
Built with CustomTkinter
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import json
import time
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

from config import (BG, BG_PANEL, BG_CARD, BORDER, ACCENT, GREEN, PINK,
                    ORANGE, PURPLE, YELLOW, RED, TEXT, DIM,
                    EMOTION_COLORS, URGENCY_COLORS, EMOTIONS, TOPICS)
from database import (initialize_db, get_stats, get_recent_articles,
                      get_emotion_distribution, get_topic_distribution,
                      get_affected_groups, search_articles)
from collector import collect_all
from analyzer import analyze_pending

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class NewsEyeDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NewsEye — News Intelligence Dashboard")
        self.geometry("1400x860")
        self.configure(fg_color=BG)
        self.resizable(True, True)
        try: self.iconbitmap("assets/icon.ico")
        except: pass

        self.current_tab  = "live"
        self.is_collecting = False
        self.is_analyzing  = False
        initialize_db()
        self._build_ui()
        self._refresh_dashboard()

    # ── UI Build ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── Sidebar ────────────────────────────────────────────────────────────
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=BG_PANEL,
                                     corner_radius=0)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(24,4))
        ctk.CTkLabel(logo_frame, text="◈ NEWSEYE",
                     font=ctk.CTkFont(family="Courier New", size=22, weight="bold"),
                     text_color=ACCENT).pack(anchor="w")
        ctk.CTkLabel(logo_frame, text="News Intelligence",
                     font=ctk.CTkFont(size=10),
                     text_color=DIM).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=BORDER).pack(fill="x", padx=16, pady=16)

        # Nav buttons
        self.nav_btns = {}
        nav_items = [
            ("live",     "⚡  Live Feed"),
            ("emotions", "🎭  Emotions"),
            ("topics",   "🏷  Topics"),
            ("groups",   "👥  Affected Groups"),
            ("search",   "🔍  Search"),
            ("sources",  "📡  Sources"),
            ("trends",   "📈  Trends"),
        ]
        for key, label in nav_items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w",
                font=ctk.CTkFont(size=13),
                fg_color="transparent",
                hover_color=BG_CARD,
                text_color=TEXT,
                corner_radius=8, height=38,
                command=lambda k=key: self._show_tab(k))
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_btns[key] = btn

        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=BORDER).pack(fill="x", padx=16, pady=16)

        # Action buttons
        ctk.CTkButton(self.sidebar, text="🔄  Collect News",
                      font=ctk.CTkFont(size=12),
                      fg_color=ACCENT, text_color=BG,
                      hover_color="#00aacc", height=36,
                      command=self._run_collect
                      ).pack(fill="x", padx=12, pady=2)

        ctk.CTkButton(self.sidebar, text="🧠  Analyze",
                      font=ctk.CTkFont(size=12),
                      fg_color=PURPLE, text_color=BG,
                      hover_color="#8866dd", height=36,
                      command=self._run_analyze
                      ).pack(fill="x", padx=12, pady=2)

        ctk.CTkButton(self.sidebar, text="⚡  Collect & Analyze",
                      font=ctk.CTkFont(size=12),
                      fg_color=GREEN, text_color=BG,
                      hover_color="#00aa55", height=36,
                      command=self._run_full_cycle
                      ).pack(fill="x", padx=12, pady=2)

        ctk.CTkButton(self.sidebar, text="📄  Generate Report",
                      font=ctk.CTkFont(size=12),
                      fg_color=YELLOW, text_color=BG,
                      hover_color="#ccaa00", height=36,
                      command=self._generate_report
                      ).pack(fill="x", padx=12, pady=4)

        # Status
        ctk.CTkFrame(self.sidebar, height=1,
                     fg_color=BORDER).pack(fill="x", padx=16, pady=8)
        self.status_label = ctk.CTkLabel(
            self.sidebar, text="● Ready",
            font=ctk.CTkFont(size=11), text_color=GREEN)
        self.status_label.pack(padx=16, pady=4, anchor="w")

        self.last_update = ctk.CTkLabel(
            self.sidebar, text="Last update: Never",
            font=ctk.CTkFont(size=9), text_color=DIM, wraplength=180)
        self.last_update.pack(padx=16, pady=2, anchor="w")

        # ── Main area ──────────────────────────────────────────────────────────
        self.main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        self.main.pack(side="left", fill="both", expand=True)

        # Top bar
        topbar = ctk.CTkFrame(self.main, height=52,
                               fg_color=BG_PANEL, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self.page_title = ctk.CTkLabel(
            topbar, text="⚡  Live Feed",
            font=ctk.CTkFont(size=16, weight="bold"), text_color=TEXT)
        self.page_title.pack(side="left", padx=24)

        # Stats row in topbar
        self.stat_labels = {}
        stats_frame = ctk.CTkFrame(topbar, fg_color="transparent")
        stats_frame.pack(side="right", padx=24)
        for key, label, color in [
            ("total",    "Total",    DIM),
            ("today",    "Today",    ACCENT),
            ("breaking", "Breaking", RED),
            ("analyzed", "Analyzed", GREEN),
        ]:
            f = ctk.CTkFrame(stats_frame, fg_color="transparent")
            f.pack(side="left", padx=12)
            ctk.CTkLabel(f, text=label,
                         font=ctk.CTkFont(size=9), text_color=DIM).pack()
            lbl = ctk.CTkLabel(f, text="0",
                               font=ctk.CTkFont(size=14, weight="bold"),
                               text_color=color)
            lbl.pack()
            self.stat_labels[key] = lbl

        ctk.CTkFrame(self.main, height=1,
                     fg_color=BORDER).pack(fill="x")

        # Content
        self.content = ctk.CTkFrame(self.main, fg_color=BG, corner_radius=0)
        self.content.pack(fill="both", expand=True)

        self._show_tab("live")

    # ── Tab Navigation ─────────────────────────────────────────────────────────
    def _show_tab(self, tab):
        self.current_tab = tab
        for key, btn in self.nav_btns.items():
            btn.configure(
                fg_color=BG_CARD if key == tab else "transparent",
                text_color=ACCENT if key == tab else TEXT)

        titles = {
            "live":     "⚡  Live Feed",
            "emotions": "🎭  Emotion Analysis",
            "topics":   "🏷  Topic Distribution",
            "groups":   "👥  Affected Groups",
            "search":   "🔍  Search & Filter",
            "sources":  "📡  News Sources",
            "trends":   "📈  Trend Detection",
        }
        self.page_title.configure(text=titles.get(tab, tab))

        for w in self.content.winfo_children():
            w.destroy()

        builders = {
            "live":     self._build_live,
            "emotions": self._build_emotions,
            "topics":   self._build_topics,
            "groups":   self._build_groups,
            "search":   self._build_search,
            "sources":  self._build_sources,
            "trends":   self._build_trends,
        }
        builders.get(tab, self._build_live)()

    # ── Live Feed ──────────────────────────────────────────────────────────────
    def _build_live(self):
        articles = get_recent_articles(limit=50, analyzed_only=True)

        if not articles:
            ctk.CTkLabel(self.content,
                         text="No analyzed articles yet.\nClick 'Collect & Analyze' to get started!",
                         font=ctk.CTkFont(size=14), text_color=DIM).pack(expand=True)
            return

        scroll = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        for article in articles:
            self._article_card(scroll, article)

    def _article_card(self, parent, article):
        emotion  = article.get("emotion", "Neutral")
        urgency  = article.get("urgency", "Background")
        topic    = article.get("topic", "")
        source   = article.get("source", "")
        title    = article.get("title", "")
        summary  = article.get("summary", "")
        reaction = article.get("public_reaction", "")
        from config import SOURCE_CREDIBILITY
        credibility = SOURCE_CREDIBILITY.get(source, article.get("credibility", 70))

        e_color = EMOTION_COLORS.get(emotion, DIM)
        u_color = URGENCY_COLORS.get(urgency, DIM)

        try:
            groups = json.loads(article.get("affected_groups", "[]"))
        except:
            groups = []

        # Card
        card = ctk.CTkFrame(parent, fg_color=BG_CARD,
                             corner_radius=10)
        card.pack(fill="x", pady=4, padx=4)

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=10)

        # Row 1 — badges
        badges = ctk.CTkFrame(inner, fg_color="transparent")
        badges.pack(fill="x")

        def badge(parent, text, color, bg=BG_PANEL):
            ctk.CTkLabel(parent, text=text,
                         font=ctk.CTkFont(size=9, weight="bold"),
                         text_color=color,
                         fg_color=bg, corner_radius=4,
                         padx=6, pady=2).pack(side="left", padx=(0,4))

        badge(badges, f"● {urgency}", u_color)
        badge(badges, emotion, e_color)
        badge(badges, topic, PURPLE)
        badge(badges, source, ACCENT)
        badge(badges, f"⭐ {credibility}%", YELLOW)

        # Row 2 — title
        ctk.CTkLabel(inner, text=title,
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=TEXT, wraplength=900,
                     anchor="w", justify="left").pack(fill="x", pady=(6,2))

        # Row 3 — summary
        if summary:
            ctk.CTkLabel(inner, text=summary[:200]+"...",
                         font=ctk.CTkFont(size=11),
                         text_color=DIM, wraplength=900,
                         anchor="w", justify="left").pack(fill="x")

        # Row 4 — affected groups + reaction
        bottom = ctk.CTkFrame(inner, fg_color="transparent")
        bottom.pack(fill="x", pady=(6,0))

        if groups:
            groups_text = "👥 " + " · ".join(groups[:4])
            ctk.CTkLabel(bottom, text=groups_text,
                         font=ctk.CTkFont(size=10),
                         text_color=ORANGE).pack(side="left")

        if reaction:
            ctk.CTkLabel(bottom,
                         text=f"  💬 {reaction[:100]}",
                         font=ctk.CTkFont(size=10),
                         text_color=DIM).pack(side="left", padx=8)

    # ── Emotions Tab ───────────────────────────────────────────────────────────
    def _build_emotions(self):
        dist = get_emotion_distribution(days=7)
        if not dist:
            ctk.CTkLabel(self.content,
                         text="No emotion data yet. Analyze some articles first.",
                         text_color=DIM).pack(expand=True)
            return

        # Split layout
        left = ctk.CTkFrame(self.content, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=16, pady=16)
        right = ctk.CTkFrame(self.content, fg_color="transparent", width=300)
        right.pack(side="right", fill="y", padx=(0,16), pady=16)
        right.pack_propagate(False)

        # Pie chart
        fig = Figure(figsize=(6,5), facecolor=BG)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(BG)

        labels = list(dist.keys())
        values = list(dist.values())
        colors = [EMOTION_COLORS.get(l, DIM) for l in labels]

        wedges, texts, autotexts = ax.pie(
            values, labels=labels, colors=colors,
            autopct="%1.1f%%", startangle=90,
            textprops={"color": TEXT, "fontsize": 11})
        for at in autotexts:
            at.set_color(BG)
            at.set_fontweight("bold")

        ax.set_title("Emotion Distribution — Last 7 Days",
                     color=TEXT, fontsize=13, pad=16)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=left)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

        # Emotion breakdown cards on right
        ctk.CTkLabel(right, text="BREAKDOWN",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=ACCENT).pack(anchor="w", pady=(0,8))

        total = sum(values) or 1
        for emotion, count in sorted(dist.items(),
                                      key=lambda x: x[1], reverse=True):
            pct   = count / total * 100
            color = EMOTION_COLORS.get(emotion, DIM)
            card  = ctk.CTkFrame(right, fg_color=BG_CARD, corner_radius=8)
            card.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=12, pady=8)
            ctk.CTkLabel(inner, text=emotion,
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=color).pack(side="left")
            ctk.CTkLabel(inner, text=f"{count} articles  ({pct:.1f}%)",
                         font=ctk.CTkFont(size=11),
                         text_color=DIM).pack(side="right")
            # Progress bar
            bar3 = ctk.CTkProgressBar(card, progress_color=color,
                               fg_color=BG_PANEL, height=4)
            bar3.pack(fill="x", padx=12, pady=(0,8))
            bar3.set(pct/100)

    # ── Topics Tab ─────────────────────────────────────────────────────────────
    def _build_topics(self):
        dist = get_topic_distribution(days=7)
        if not dist:
            ctk.CTkLabel(self.content,
                         text="No topic data yet.",
                         text_color=DIM).pack(expand=True)
            return

        fig = Figure(figsize=(10,5), facecolor=BG)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(BG_PANEL)

        topics = list(dist.keys())
        counts = list(dist.values())
        colors = [ACCENT, PURPLE, GREEN, ORANGE, PINK,
                  YELLOW, RED, "#00ccff", "#ff66aa", "#66ffcc"][:len(topics)]

        bars = ax.barh(topics, counts, color=colors, height=0.6)
        ax.set_facecolor(BG_PANEL)
        ax.tick_params(colors=TEXT, labelsize=11)
        ax.spines[:].set_color(BORDER)
        ax.set_xlabel("Article Count", color=DIM, fontsize=10)
        ax.set_title("Topic Distribution — Last 7 Days",
                     color=TEXT, fontsize=13, pad=16)
        fig.patch.set_facecolor(BG)

        for bar, count in zip(bars, counts):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
                    str(count), va="center", color=TEXT, fontsize=10)

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.content)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True,
                                    padx=16, pady=16)

    # ── Affected Groups Tab ────────────────────────────────────────────────────
    def _build_groups(self):
        groups = get_affected_groups(days=7)
        if not groups:
            ctk.CTkLabel(self.content,
                         text="No affected groups data yet.",
                         text_color=DIM).pack(expand=True)
            return

        scroll = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(scroll, text="Most Affected Groups — Last 7 Days",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0,12))

        max_count = max(groups.values()) or 1
        colors    = [PINK, ORANGE, YELLOW, GREEN, ACCENT,
                     PURPLE, RED, "#00ccff", "#ff66aa", "#66ffcc"]

        for i, (group, count) in enumerate(groups.items()):
            color = colors[i % len(colors)]
            card  = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8)
            card.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            ctk.CTkLabel(inner, text=f"#{i+1}",
                         font=ctk.CTkFont(size=11),
                         text_color=DIM, width=30).pack(side="left")
            ctk.CTkLabel(inner, text=group,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=color).pack(side="left", padx=8)
            ctk.CTkLabel(inner, text=f"{count} mentions",
                         font=ctk.CTkFont(size=11),
                         text_color=DIM).pack(side="right")

            pct = count / max_count
            bar1 = ctk.CTkProgressBar(card, progress_color=color,
                               fg_color=BG_PANEL, height=4)
            bar1.pack(fill="x", padx=14, pady=(0,10))
            bar1.set(pct)

    # ── Search Tab ─────────────────────────────────────────────────────────────
    def _build_search(self):
        # Filters bar
        filters = ctk.CTkFrame(self.content, fg_color=BG_PANEL,
                               corner_radius=0)
        filters.pack(fill="x", padx=0, pady=0)

        inner = ctk.CTkFrame(filters, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=12)

        kw_var   = ctk.StringVar()
        src_var  = ctk.StringVar(value="All Sources")
        top_var  = ctk.StringVar(value="All Topics")
        emo_var  = ctk.StringVar(value="All Emotions")
        urg_var  = ctk.StringVar(value="All Urgency")

        ctk.CTkEntry(inner, textvariable=kw_var,
                     placeholder_text="Search keyword...",
                     width=200, fg_color=BG_CARD,
                     border_color=BORDER).pack(side="left", padx=(0,8))

        sources = ["All Sources", "AP News", "Reuters", "BBC News",
                   "Al Jazeera", "The Guardian", "France 24",
                   "DW", "NY Times", "South China Morning Post",
                   "Egypt Independent"]
        ctk.CTkOptionMenu(inner, variable=src_var, values=sources,
                          fg_color=BG_CARD, button_color=BORDER,
                          width=160).pack(side="left", padx=(0,8))

        ctk.CTkOptionMenu(inner, variable=top_var,
                          values=["All Topics"] + TOPICS,
                          fg_color=BG_CARD, button_color=BORDER,
                          width=160).pack(side="left", padx=(0,8))

        ctk.CTkOptionMenu(inner, variable=emo_var,
                          values=["All Emotions"] + EMOTIONS,
                          fg_color=BG_CARD, button_color=BORDER,
                          width=140).pack(side="left", padx=(0,8))

        ctk.CTkOptionMenu(inner, variable=urg_var,
                          values=["All Urgency",
                                  "Breaking","Developing","Background"],
                          fg_color=BG_CARD, button_color=BORDER,
                          width=130).pack(side="left", padx=(0,8))

        results_frame = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        results_frame.pack(fill="both", expand=True, padx=16, pady=8)

        def do_search():
            for w in results_frame.winfo_children():
                w.destroy()
            articles = search_articles(
                keyword=kw_var.get(),
                source="" if src_var.get() == "All Sources" else src_var.get(),
                topic=""  if top_var.get() == "All Topics"  else top_var.get(),
                emotion="" if emo_var.get() == "All Emotions" else emo_var.get(),
                urgency="" if urg_var.get() == "All Urgency"  else urg_var.get(),
            )
            ctk.CTkLabel(results_frame,
                         text=f"{len(articles)} results",
                         font=ctk.CTkFont(size=11),
                         text_color=DIM).pack(anchor="w", pady=(0,8))
            for a in articles:
                self._article_card(results_frame, a)

        ctk.CTkButton(inner, text="Search",
                      fg_color=ACCENT, text_color=BG,
                      command=do_search, width=80).pack(side="left")

        do_search()

    # ── Sources Tab ────────────────────────────────────────────────────────────
    def _build_sources(self):
        from config import ALL_SOURCES, SOURCE_CREDIBILITY
        from database import get_connection

        scroll = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(scroll, text="News Sources & Credibility",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0,12))

        conn = get_connection()
        for name, url in ALL_SOURCES.items():
            credibility = SOURCE_CREDIBILITY.get(name, 70)
            row = conn.execute(
                "SELECT COUNT(*) FROM articles WHERE source=?",
                (name,)).fetchone()
            count = row[0] if row else 0

            color = (GREEN if credibility >= 88 else
                     ACCENT if credibility >= 80 else
                     ORANGE if credibility >= 72 else PINK)

            card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8)
            card.pack(fill="x", pady=3)
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=14, pady=10)

            ctk.CTkLabel(inner, text=name,
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=TEXT).pack(side="left")

            ctk.CTkLabel(inner,
                         text=f"⭐ {credibility}% credibility",
                         font=ctk.CTkFont(size=11),
                         text_color=color).pack(side="right", padx=8)
            ctk.CTkLabel(inner,
                         text=f"{count} articles",
                         font=ctk.CTkFont(size=11),
                         text_color=DIM).pack(side="right")

            bar2 = ctk.CTkProgressBar(card, progress_color=color,
                               fg_color=BG_PANEL, height=4)
            bar2.pack(fill="x", padx=14, pady=(0,10))
            bar2.set(credibility/100)
        conn.close()

    # ── Actions ────────────────────────────────────────────────────────────────
    def _run_collect(self):
        if self.is_collecting: return
        self.is_collecting = True
        self.status_label.configure(text="● Collecting...", text_color=YELLOW)

        def run():
            collect_all(on_progress=lambda m:
                self.status_label.configure(text=f"● {m[:30]}"))
            self.is_collecting = False
            self.after(0, self._refresh_dashboard)

        threading.Thread(target=run, daemon=True).start()

    def _run_analyze(self):
        if self.is_analyzing: return
        self.is_analyzing = True
        self.status_label.configure(text="● Analyzing...", text_color=PURPLE)

        def run():
            analyzed = 0
            while True:
                batch = analyze_pending(
                    batch_size=3,
                    on_progress=lambda m:
                        self.status_label.configure(
                            text=f"● {m[:30]}"))
                if batch == 0: break
                analyzed += batch
            self.is_analyzing = False
            self.after(0, self._refresh_dashboard)

        threading.Thread(target=run, daemon=True).start()

    def _run_full_cycle(self):
        if self.is_collecting or self.is_analyzing: return
        self.status_label.configure(
            text="● Full cycle...", text_color=GREEN)

        def run():
            self.is_collecting = True
            collect_all(on_progress=lambda m:
                self.status_label.configure(text=f"● {m[:30]}"))
            self.is_collecting = False
            self.is_analyzing  = True
            while True:
                batch = analyze_pending(batch_size=3)
                if batch == 0: break
            self.is_analyzing = False
            self.after(0, self._refresh_dashboard)

        threading.Thread(target=run, daemon=True).start()

    def _refresh_dashboard(self):
        stats = get_stats()
        for key, lbl in self.stat_labels.items():
            lbl.configure(text=str(stats.get(key, 0)))

        self.status_label.configure(text="● Ready", text_color=GREEN)
        self.last_update.configure(
            text=f"Updated: {datetime.now().strftime('%H:%M:%S')}")

        if self.current_tab in ("live", "emotions", "topics", "groups"):
            self._show_tab(self.current_tab)


    # ── Trends ────────────────────────────────────────────────────────────────
    def _build_trends(self):
        from database import get_trending_keywords, get_emotion_trend, get_breaking_trend
        import matplotlib
        matplotlib.use("Agg")
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        scroll = ctk.CTkScrollableFrame(self.content, fg_color=BG)
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # ── Trending Keywords ────────────────────────────────────────────────
        ctk.CTkLabel(scroll, text="🔥  Trending Keywords",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(0,8))

        keywords = get_trending_keywords(limit=10)
        if keywords:
            for i, (word, count, change) in enumerate(keywords):
                color  = GREEN if change > 0 else PINK
                arrow  = "↑" if change > 0 else "↓"
                change_text = f"{arrow} {abs(change):.0f}%"

                card = ctk.CTkFrame(scroll, fg_color=BG_CARD, corner_radius=8)
                card.pack(fill="x", pady=3)
                inner = ctk.CTkFrame(card, fg_color="transparent")
                inner.pack(fill="x", padx=14, pady=10)

                ctk.CTkLabel(inner, text=f"#{i+1}",
                             font=ctk.CTkFont(size=11),
                             text_color=DIM, width=30).pack(side="left")
                ctk.CTkLabel(inner, text=word,
                             font=ctk.CTkFont(size=13, weight="bold"),
                             text_color=ACCENT).pack(side="left", padx=8)
                ctk.CTkLabel(inner, text=f"{count} mentions",
                             font=ctk.CTkFont(size=11),
                             text_color=DIM).pack(side="left")
                ctk.CTkLabel(inner, text=change_text,
                             font=ctk.CTkFont(size=12, weight="bold"),
                             text_color=color).pack(side="right", padx=8)
        else:
            ctk.CTkLabel(scroll, text="Not enough data for trend analysis yet.",
                         text_color=DIM).pack(anchor="w", pady=8)

        # ── Emotion Trend Chart ──────────────────────────────────────────────
        ctk.CTkLabel(scroll, text="🎭  Emotion Trend — Last 7 Days",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(20,8))

        emotion_trend = get_emotion_trend(days=7)
        if len(emotion_trend) > 1:
            fig = Figure(figsize=(9, 3.5), facecolor=BG)
            ax  = fig.add_subplot(111)
            ax.set_facecolor(BG_PANEL)

            days_list = sorted(emotion_trend.keys())
            emotions  = ["Fear","Anger","Hope","Sadness","Excitement","Neutral"]
            e_colors  = [RED, ORANGE, GREEN,
                         "#6699ff", YELLOW, DIM]

            for emotion, color in zip(emotions, e_colors):
                values = [emotion_trend[d].get(emotion, 0) for d in days_list]
                if any(v > 0 for v in values):
                    ax.plot(days_list, values, marker="o", linewidth=2,
                            color=color, label=emotion, markersize=4)

            ax.tick_params(colors=TEXT, labelsize=8)
            ax.spines[:].set_color(BORDER)
            ax.set_xlabel("Date", color=DIM, fontsize=9)
            ax.set_ylabel("Articles", color=DIM, fontsize=9)
            ax.legend(loc="upper left", fontsize=8,
                      facecolor=BG_CARD, edgecolor=BORDER,
                      labelcolor=TEXT)
            fig.tight_layout()

            chart_frame = ctk.CTkFrame(scroll, fg_color=BG_PANEL,
                                        corner_radius=10)
            chart_frame.pack(fill="x", pady=(0,8))
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="x", padx=8, pady=8)
            plt.close(fig)
        else:
            ctk.CTkLabel(scroll,
                         text="Need data from multiple days for trend chart.",
                         text_color=DIM).pack(anchor="w", pady=4)

        # ── Breaking News Trend ──────────────────────────────────────────────
        ctk.CTkLabel(scroll, text="⚡  Breaking News Volume — Last 7 Days",
                     font=ctk.CTkFont(size=14, weight="bold"),
                     text_color=TEXT).pack(anchor="w", pady=(20,8))

        breaking_trend = get_breaking_trend(days=7)
        if len(breaking_trend) > 1:
            fig2 = Figure(figsize=(9, 2.5), facecolor=BG)
            ax2  = fig2.add_subplot(111)
            ax2.set_facecolor(BG_PANEL)

            days2  = sorted(breaking_trend.keys())
            counts = [breaking_trend[d] for d in days2]

            ax2.bar(days2, counts, color=RED, alpha=0.8, width=0.6)
            ax2.plot(days2, counts, color=ORANGE, linewidth=2,
                     marker="o", markersize=5)

            ax2.tick_params(colors=TEXT, labelsize=8)
            ax2.spines[:].set_color(BORDER)
            ax2.set_ylabel("Breaking Articles", color=DIM, fontsize=9)
            fig2.tight_layout()

            chart_frame2 = ctk.CTkFrame(scroll, fg_color=BG_PANEL,
                                         corner_radius=10)
            chart_frame2.pack(fill="x", pady=(0,8))
            canvas2 = FigureCanvasTkAgg(fig2, master=chart_frame2)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill="x", padx=8, pady=8)
            plt.close(fig2)
        else:
            ctk.CTkLabel(scroll,
                         text="Need data from multiple days for breaking news trend.",
                         text_color=DIM).pack(anchor="w", pady=4)

    def _generate_report(self):
        self.status_label.configure(text="● Generating PDF...", text_color=YELLOW)
        def run():
            from reporter import build_report
            import os
            path     = build_report()
            abs_path = os.path.abspath(path)
            os.startfile(abs_path)
            self.after(0, lambda: self.status_label.configure(
                text="● Report ready!", text_color=GREEN))
        threading.Thread(target=run, daemon=True).start()


    def on_closing(self):
        self.destroy()

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = NewsEyeDashboard()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()