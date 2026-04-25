"""
reporter.py — PDF Intelligence Brief Generator for NewsEyeNewsEye
Generates a professional daily intelligence report
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak,
    Table, TableStyle, HRFlowable
)
from reportlab.graphics.shapes import Drawing, Rect, Circle, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import HorizontalBarChart
from reportlab.graphics import renderPDF
import json
import os
from datetime import datetime, timedelta
from database import (get_stats, get_recent_articles, get_emotion_distribution,
                      get_topic_distribution, get_affected_groups,
                      search_articles, get_connection)
from config import EMOTION_COLORS, URGENCY_COLORS, SOURCE_CREDIBILITY

# ── Colors ─────────────────────────────────────────────────────────────────────
C_BG      = colors.HexColor("#0a0e1a")
C_PANEL   = colors.HexColor("#111827")
C_CARD    = colors.HexColor("#1a2235")
C_ACCENT  = colors.HexColor("#00d4ff")
C_GREEN   = colors.HexColor("#00cc66")
C_PINK    = colors.HexColor("#e94560")
C_ORANGE  = colors.HexColor("#ff9944")
C_PURPLE  = colors.HexColor("#aa88ff")
C_YELLOW  = colors.HexColor("#ffd700")
C_RED     = colors.HexColor("#ff4444")
C_TEXT    = colors.HexColor("#e8eaf0")
C_DIM     = colors.HexColor("#8892a4")
C_WHITE   = colors.white
C_BORDER  = colors.HexColor("#1e2d42")

RL_EMOTION_COLORS = {
    "Fear":       C_RED,
    "Anger":      C_ORANGE,
    "Hope":       C_GREEN,
    "Sadness":    colors.HexColor("#6699ff"),
    "Excitement": C_YELLOW,
    "Neutral":    C_DIM,
}

SF  = "Helvetica"
SFB = "Helvetica-Bold"
MONO = "Courier"

W, H = letter

# ── Styles ─────────────────────────────────────────────────────────────────────
def S(name, **kw):
    base = dict(fontName=SF, fontSize=11, textColor=C_TEXT, leading=16, spaceAfter=5)
    base.update(kw)
    return ParagraphStyle(name, **base)

ST = {
    "cover_title":  S("ct", fontName=SFB, fontSize=38, textColor=C_ACCENT,
                      alignment=TA_CENTER, spaceAfter=8),
    "cover_sub":    S("cs", fontSize=13, textColor=C_DIM, alignment=TA_CENTER),
    "cover_class":  S("cc", fontName=SFB, fontSize=10, textColor=C_GREEN,
                      alignment=TA_CENTER),
    "section":      S("se", fontName=SFB, fontSize=16, textColor=C_ACCENT,
                      spaceBefore=16, spaceAfter=6),
    "subsection":   S("ss", fontName=SFB, fontSize=12, textColor=C_PINK,
                      spaceBefore=10, spaceAfter=4),
    "body":         S("bo", fontSize=11, textColor=C_TEXT, leading=17),
    "body_dim":     S("bd", fontSize=10, textColor=C_DIM, leading=15),
    "article_title":S("at", fontName=SFB, fontSize=12, textColor=C_TEXT,
                      spaceBefore=8, spaceAfter=2),
    "article_meta": S("am", fontSize=9, textColor=C_DIM, spaceAfter=3),
    "article_body": S("ab", fontSize=10, textColor=C_DIM, leading=14, spaceAfter=6),
    "stat_num":     S("sn", fontName=SFB, fontSize=28, textColor=C_ACCENT,
                      alignment=TA_CENTER, spaceAfter=2),
    "stat_label":   S("sl", fontSize=9, textColor=C_DIM, alignment=TA_CENTER),
    "highlight":    S("hl", fontName=SFB, fontSize=12, textColor=C_YELLOW,
                      spaceBefore=6, spaceAfter=4),
    "reaction":     S("re", fontSize=10, textColor=C_DIM,
                      leftIndent=12, spaceAfter=4),
}

def on_page(canvas, doc):
    canvas.saveState()
    # Dark background
    canvas.setFillColor(C_BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # Cyan top bar
    canvas.setFillColor(C_ACCENT)
    canvas.rect(0, H-3, W, 3, fill=1, stroke=0)
    # Footer line
    canvas.setStrokeColor(C_BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(0.5*inch, 0.55*inch, W-0.5*inch, 0.55*inch)
    # Footer text
    canvas.setFont(SF, 8)
    canvas.setFillColor(C_DIM)
    canvas.drawString(0.5*inch, 0.35*inch,
        "PULSE — News Intelligence Platform  |  Open Source Intelligence")
    canvas.drawCentredString(W/2, 0.35*inch,
        f"Generated: {datetime.now().strftime('%B %d, %Y  %H:%M')}")
    canvas.drawRightString(W-0.5*inch, 0.35*inch, f"Page {doc.page}")
    canvas.restoreState()

def p(s, t):   return Paragraph(t, ST[s])
def sp(n=8):   return Spacer(1, n)
def hr(c=C_ACCENT): return HRFlowable(width="100%", thickness=0.5, color=c)
def hr_dim():  return HRFlowable(width="100%", thickness=0.3, color=C_BORDER)

def color_badge(text, color):
    """Inline colored text badge."""
    hex_color = color.hexval() if hasattr(color, 'hexval') else "#00d4ff"
    return f'<font color="{hex_color}"><b>{text}</b></font>'

def make_stat_table(stats):
    """4-column stat table for executive summary."""
    breaking = stats.get("breaking", 0)
    data = [[
        Paragraph(str(stats.get("total",0)),    ST["stat_num"]),
        Paragraph(str(stats.get("today",0)),     ST["stat_num"]),
        Paragraph(str(breaking),                 ParagraphStyle("br", fontName=SFB,
            fontSize=28, textColor=C_RED, alignment=TA_CENTER, spaceAfter=2)),
        Paragraph(str(stats.get("analyzed",0)),  ParagraphStyle("an", fontName=SFB,
            fontSize=28, textColor=C_GREEN, alignment=TA_CENTER, spaceAfter=2)),
    ],[
        Paragraph("Total Articles",  ST["stat_label"]),
        Paragraph("Today",           ST["stat_label"]),
        Paragraph("Breaking",        ParagraphStyle("brl", fontSize=9,
            textColor=C_RED, alignment=TA_CENTER)),
        Paragraph("Analyzed",        ParagraphStyle("anl", fontSize=9,
            textColor=C_GREEN, alignment=TA_CENTER)),
    ]]
    t = Table(data, colWidths=[2.2*inch]*4)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_PANEL),
        ("ROWBACKGROUNDS",(0,0), (-1,-1), [C_PANEL]),
        ("TOPPADDING",    (0,0), (-1,-1), 12),
        ("BOTTOMPADDING", (0,0), (-1,-1), 12),
        ("LINEAFTER",     (0,0), (2,1),   0.5, C_BORDER),
        ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
    ]))
    return t

def make_emotion_chart(dist):
    """Pie chart for emotion distribution."""
    if not dist: return None
    drawing = Drawing(280, 200)
    pie = Pie()
    pie.x = 60
    pie.y = 20
    pie.width  = 160
    pie.height = 160
    pie.data   = list(dist.values())
    pie.labels = list(dist.keys())
    pie.slices.strokeWidth = 0.5
    pie.slices.strokeColor = C_BG
    colors_list = [RL_EMOTION_COLORS.get(l, C_DIM) for l in dist.keys()]
    for i, c in enumerate(colors_list):
        pie.slices[i].fillColor = c
        pie.slices[i].labelRadius = 1.2
    pie.sideLabels    = True
    pie.sideLabelsOffset = 0.1
    drawing.add(pie)
    return drawing

def make_topic_chart(dist):
    """Horizontal bar chart for topics."""
    if not dist: return None
    drawing = Drawing(450, max(120, len(dist)*28))
    chart = HorizontalBarChart()
    chart.x = 120
    chart.y = 10
    chart.width  = 300
    chart.height = max(100, len(dist)*24)
    chart.data   = [list(dist.values())]
    chart.categoryAxis.categoryNames = list(dist.keys())
    chart.categoryAxis.labels.fontName  = SF
    chart.categoryAxis.labels.fontSize  = 9
    chart.categoryAxis.labels.fillColor = C_TEXT
    chart.valueAxis.labels.fontName     = SF
    chart.valueAxis.labels.fontSize     = 8
    chart.valueAxis.labels.fillColor    = C_DIM
    chart.bars[0].fillColor   = C_ACCENT
    chart.bars[0].strokeColor = C_BG
    chart.bars[0].strokeWidth = 0
    chart.valueAxis.strokeColor    = C_BORDER
    chart.categoryAxis.strokeColor = C_BORDER
    drawing.add(chart)
    return drawing

def urgency_color(urgency):
    mapping = {"Breaking": C_RED, "Developing": C_ORANGE, "Background": C_DIM}
    return mapping.get(urgency, C_DIM)

def emotion_color(emotion):
    return RL_EMOTION_COLORS.get(emotion, C_DIM)

# ── Main Report Builder ────────────────────────────────────────────────────────
def build_report(output_path=None):
    if not output_path:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        output_path = f"reports/Pulse_Brief_{ts}.pdf"

    os.makedirs("reports", exist_ok=True)

    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        leftMargin=0.65*inch, rightMargin=0.65*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch)

    story = []
    stats   = get_stats()
    now     = datetime.now()

    # ── PAGE 1: COVER ──────────────────────────────────────────────────────────
    story += [
        sp(60),
        p("cover_class", "◈  OPEN SOURCE INTELLIGENCE  ◈"),
        sp(16),
        p("cover_title", "PULSE"),
        sp(4),
        p("cover_sub", "Daily Intelligence Brief"),
        sp(8),
        hr(),
        sp(8),
        p("cover_sub", now.strftime("%A, %B %d, %Y  —  %H:%M")),
        sp(4),
        p("cover_sub", f"Monitoring {len(SOURCE_CREDIBILITY)} global sources  ·  {stats['total']} articles collected"),
        sp(60),
    ]

    # dominant emotion + top story
    dom_emotion = stats.get("dominant_emotion", "N/A")
    dom_topic   = stats.get("dominant_topic", "N/A")
    ec = RL_EMOTION_COLORS.get(dom_emotion, C_DIM)

    cover_data = [[
        Paragraph("Dominant Emotion", ST["stat_label"]),
        Paragraph("Top Topic", ST["stat_label"]),
        Paragraph("Breaking Stories", ST["stat_label"]),
    ],[
        Paragraph(dom_emotion, ParagraphStyle("de", fontName=SFB, fontSize=18,
            textColor=ec, alignment=TA_CENTER)),
        Paragraph(dom_topic,   ParagraphStyle("dt", fontName=SFB, fontSize=18,
            textColor=C_PURPLE, alignment=TA_CENTER)),
        Paragraph(str(stats.get("breaking",0)), ParagraphStyle("db", fontName=SFB,
            fontSize=18, textColor=C_RED, alignment=TA_CENTER)),
    ]]
    cover_t = Table(cover_data, colWidths=[2.7*inch]*3)
    cover_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), C_CARD),
        ("BOX",           (0,0), (-1,-1), 0.5, C_BORDER),
        ("LINEAFTER",     (0,0), (1,1),   0.5, C_BORDER),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story += [cover_t, PageBreak()]

    # ── PAGE 2: EXECUTIVE SUMMARY ──────────────────────────────────────────────
    story += [p("section", "EXECUTIVE SUMMARY"), hr(), sp(8),
              make_stat_table(stats), sp(16)]

    # Top affected groups
    groups = get_affected_groups(days=1)
    if groups:
        story += [p("subsection", "Most Affected Groups Today"), sp(4)]
        top5 = list(groups.items())[:5]
        g_data = [["Rank", "Group", "Mentions"]]
        for i, (g, c) in enumerate(top5, 1):
            g_data.append([f"#{i}", g, str(c)])
        gt = Table(g_data, colWidths=[0.6*inch, 5.0*inch, 1.0*inch])
        gt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  C_ACCENT),
            ("TEXTCOLOR",     (0,0), (-1,0),  C_BG),
            ("FONTNAME",      (0,0), (-1,0),  SFB),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("BACKGROUND",    (0,1), (-1,-1), C_CARD),
            ("TEXTCOLOR",     (0,1), (-1,-1), C_TEXT),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_CARD, C_PANEL]),
            ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story += [gt, sp(8)]

    # Top story
    breaking = search_articles(urgency="Breaking", limit=1)
    if breaking:
        top = breaking[0]
        story += [
            p("subsection", "Top Story"),
            p("article_title", top.get("title","")),
            p("article_meta",
              f"{top.get('source','')}  ·  {top.get('emotion','')}  ·  {top.get('topic','')}"),
            p("body_dim", top.get("summary","")[:300]+"..."),
        ]
        try:
            grps = json.loads(top.get("affected_groups","[]"))
            if grps:
                story.append(p("reaction",
                    f"👥 Affected: {', '.join(grps[:4])}"))
            react = top.get("public_reaction","")
            if react:
                story.append(p("reaction", f"💬 {react}"))
        except: pass

    story.append(PageBreak())

    # ── PAGE 3: BREAKING NEWS ──────────────────────────────────────────────────
    story += [p("section", "BREAKING NEWS"), hr(), sp(8)]
    breaking_all = search_articles(urgency="Breaking", limit=20)
    if not breaking_all:
        story.append(p("body_dim", "No breaking news at this time."))
    else:
        for art in breaking_all:
            emotion = art.get("emotion","Neutral")
            ec2     = RL_EMOTION_COLORS.get(emotion, C_DIM)
            story += [
                p("article_title", art.get("title","")),
                p("article_meta",
                  f"Source: {art.get('source','')}  ·  "
                  f"Emotion: {emotion}  ·  "
                  f"Topic: {art.get('topic','')}  ·  "
                  f"Credibility: {art.get('credibility',0)}%"),
            ]
            if art.get("summary"):
                story.append(p("article_body", art["summary"][:200]+"..."))
            try:
                grps = json.loads(art.get("affected_groups","[]"))
                if grps:
                    story.append(p("reaction",
                        f"👥 {', '.join(grps[:4])}"))
                react = art.get("public_reaction","")
                if react:
                    story.append(p("reaction", f"💬 {react[:120]}"))
            except: pass
            story.append(hr_dim())

    story.append(PageBreak())

    # ── PAGE 4: EMOTION ANALYSIS ───────────────────────────────────────────────
    story += [p("section", "EMOTION ANALYSIS"), hr(), sp(8)]
    emotion_dist = get_emotion_distribution(days=1)
    if emotion_dist:
        chart = make_emotion_chart(emotion_dist)
        if chart:
            story.append(chart)
            story.append(sp(8))

        # Table breakdown
        total_e = sum(emotion_dist.values()) or 1
        e_data  = [["Emotion", "Articles", "Percentage"]]
        for emotion, count in sorted(emotion_dist.items(),
                                      key=lambda x: x[1], reverse=True):
            pct = count / total_e * 100
            e_data.append([emotion, str(count), f"{pct:.1f}%"])

        et = Table(e_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
        et.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  C_PURPLE),
            ("TEXTCOLOR",     (0,0), (-1,0),  C_BG),
            ("FONTNAME",      (0,0), (-1,0),  SFB),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("BACKGROUND",    (0,1), (-1,-1), C_CARD),
            ("TEXTCOLOR",     (0,1), (-1,-1), C_TEXT),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_CARD, C_PANEL]),
            ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story += [et, sp(8)]
    else:
        story.append(p("body_dim", "No emotion data available yet."))

    story.append(PageBreak())

    # ── PAGE 5: TOPIC DISTRIBUTION ─────────────────────────────────────────────
    story += [p("section", "TOPIC DISTRIBUTION"), hr(), sp(8)]
    topic_dist = get_topic_distribution(days=1)
    if topic_dist:
        chart2 = make_topic_chart(topic_dist)
        if chart2:
            story.append(chart2)
            story.append(sp(8))

        t_data = [["Topic", "Articles"]]
        for topic, count in sorted(topic_dist.items(),
                                    key=lambda x: x[1], reverse=True):
            t_data.append([topic, str(count)])
        tt = Table(t_data, colWidths=[4.0*inch, 1.5*inch])
        tt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  C_GREEN),
            ("TEXTCOLOR",     (0,0), (-1,0),  C_BG),
            ("FONTNAME",      (0,0), (-1,0),  SFB),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("BACKGROUND",    (0,1), (-1,-1), C_CARD),
            ("TEXTCOLOR",     (0,1), (-1,-1), C_TEXT),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_CARD, C_PANEL]),
            ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story += [tt]
    else:
        story.append(p("body_dim", "No topic data available yet."))

    story.append(PageBreak())

    # ── PAGE 6: AFFECTED GROUPS ────────────────────────────────────────────────
    story += [p("section", "AFFECTED GROUPS"), hr(), sp(8)]
    all_groups = get_affected_groups(days=1)
    if all_groups:
        ag_data = [["Rank", "Group / Community", "Mentions"]]
        for i, (g, c) in enumerate(all_groups.items(), 1):
            ag_data.append([f"#{i}", g, str(c)])
        agt = Table(ag_data, colWidths=[0.6*inch, 5.0*inch, 1.0*inch])
        agt.setStyle(TableStyle([
            ("BACKGROUND",    (0,0), (-1,0),  C_PINK),
            ("TEXTCOLOR",     (0,0), (-1,0),  C_BG),
            ("FONTNAME",      (0,0), (-1,0),  SFB),
            ("FONTSIZE",      (0,0), (-1,-1), 10),
            ("BACKGROUND",    (0,1), (-1,-1), C_CARD),
            ("TEXTCOLOR",     (0,1), (-1,-1), C_TEXT),
            ("ROWBACKGROUNDS",(0,1), (-1,-1), [C_CARD, C_PANEL]),
            ("GRID",          (0,0), (-1,-1), 0.3, C_BORDER),
            ("TOPPADDING",    (0,0), (-1,-1), 6),
            ("BOTTOMPADDING", (0,0), (-1,-1), 6),
            ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ]))
        story += [agt]
    else:
        story.append(p("body_dim", "No affected groups data yet."))

    story.append(PageBreak())

    # ── PAGE 7: FULL ARTICLE LOG ───────────────────────────────────────────────
    story += [p("section", "FULL ARTICLE LOG"), hr(), sp(8),
              p("body_dim", f"All analyzed articles — {now.strftime('%B %d, %Y')}"),
              sp(8)]

    all_articles = get_recent_articles(limit=100, analyzed_only=True)
    for art in all_articles:
        urgency = art.get("urgency","Background")
        emotion = art.get("emotion","Neutral")
        uc      = urgency_color(urgency)

        story += [
            p("article_title", art.get("title","")),
            p("article_meta",
              f"{art.get('source','')}  ·  {urgency}  ·  "
              f"{emotion}  ·  {art.get('topic','')}  ·  "
              f"Credibility: {art.get('credibility',0)}%"),
        ]
        try:
            grps = json.loads(art.get("affected_groups","[]"))
            if grps:
                story.append(p("reaction", f"👥 {', '.join(grps[:5])}"))
            react = art.get("public_reaction","")
            if react:
                story.append(p("reaction", f"💬 {react[:150]}"))
        except: pass
        story.append(hr_dim())

    # Build
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"✅ Report generated: {output_path}")
    return output_path

# ── Test ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from database import initialize_db
    initialize_db()
    path = build_report()
    print(f"Report saved to: {path}")
    import os
    os.startfile(path)  # Opens PDF automatically on Windows
